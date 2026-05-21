# "Run in Backend" — 实现分析与本地复现

## 概述

XJupyterLite 的 **"Run in backend"** 按钮允许用户把当前正在编辑的 notebook
直接提交到 AKS 集群执行，无需先 publish 为 template。本文档解释其实现原理，
并分析如何在本地用脚本做同样的事情。

---

## 前端实现流程

### 1. 按钮点击 → 弹出对话框

文件: `TemplateViewerNotebookTool.tsx`

```
用户点击 "Run in backend" 按钮
  → 弹出 Dialog，用户可输入 InputParametersJson（可选）
  → 用户点击 "Run"
```

### 2. 两步提交

文件: `handler.ts` → `runNotebookNow()`

```
Step 1: POST /api/v1/XJupyterlite/SubmitAKSJob
  body: {
    Script: "_temp_run",           ← 特殊标识，表示临时运行
    InputParametersJson: "...",
    SubmittedBy: "TemporaryRunNotebook",
    Environment: "Test"
  }
  返回: job_id (GUID)

Step 2: POST /api/v1/XJupyterlite/SavePickleObj?storageId={job_id}_temp_run
  body: notebook JSON 内容
  → 上传到 blob container "xjupyterlite-pythonobj"
  → blob name: "{job_id}_temp_run"
```

### 3. 后端处理

```
SubmitAKSJob API
  → 发送 ServiceBus 消息到 jupyternotebookqueue
  → ClusterMaster (python-worker-deployment) 收到消息
    → create_job_entity(): 识别 _temp_run 格式，template_path = "TemporaryRunNotebook"
    → create_job(): 创建 K8s Job
      → jupyter-job-{job_id} pod 启动

tryExecute.py (在 worker pod 中)
  → 检测到 blob_id 以 "_temp_run" 结尾
  → 从 "xjupyterlite-pythonobj" container 下载 notebook JSON
  → 执行 notebook
  → 上传 HTML report 到 "xjupyterlite-report" container
```

### 4. 查看结果

```
Report URL: https://aka.ms/xjplreport?path={job_id}_temp_run.html
```

---

## 完整数据流图

```
┌──────────────────────────────────────────────────────────────────┐
│ Browser (XJupyterLite)                                          │
│                                                                  │
│  1. POST SubmitAKSJob {Script: "_temp_run"} → 获得 job_id       │
│  2. POST SavePickleObj?storageId={job_id}_temp_run               │
│     body = notebook JSON                                         │
└───────────────┬──────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────┐
│ XPortal Backend API                                              │
│                                                                  │
│  SubmitAKSJob → ServiceBus message → jupyternotebookqueue       │
│  SavePickleObj → Blob Storage (xjupyterlite-pythonobj)          │
└───────────────┬──────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────┐
│ AKS Cluster                                                      │
│                                                                  │
│  ClusterMaster (python-worker-deployment)                        │
│    → 收到 ServiceBus 消息                                        │
│    → 创建 K8s Job: jupyter-job-{job_id}                         │
│                                                                  │
│  Worker Pod (python-client-image)                                │
│    → tryExecute.py                                               │
│    → 从 blob 下载 notebook JSON                                  │
│    → 如有 ZEROTOIL_PACKAGE_VERSION → pip install zerotoil        │
│    → 执行 notebook cells                                         │
│    → 上传 HTML report                                            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 本地复现分析

### 已有脚本: `run_job_locally.py`

`src/scripts/run_job_locally.py` **已经可以做类似的事情**，但它只支持
提交已存在的 template（从 ADO repo 拉取），不支持上传临时 notebook 内容。

它的工作方式是直接往 ServiceBus 发消息（跳过了 XPortal API）：

```python
message = {
    "BlobId": f"{job_id}_{NOTEBOOK_PATH}",
    "Script": NOTEBOOK_PATH,              # 例如 "/Xstore/HelloWorld.ipynb"
    "InputParametersJson": params,
    "SubmittedBy": "XJPLTrigger",
    ...
}
sender.send_messages(ServiceBusMessage(json.dumps(message)))
```

### 如何在本地实现 "Run in backend"

要完全复现 "Run in backend"，本地脚本需要做两件事：

#### 方案 A: 通过 ServiceBus 直接发消息（推荐，和 run_job_locally.py 一致）

```python
# 1. 生成 job_id
job_id = str(uuid.uuid4())
blob_id = f"{job_id}_temp_run"

# 2. 上传 notebook 到 blob（使用 XJPLAzureStorageCredential）
credential = XJPLAzureStorageCredential()
blob_client = BlobClient(
    account_url="https://xportals.blob.core.windows.net",
    container_name="xjupyterlite-pythonobj",
    blob_name=blob_id,
    credential=credential,
)
with open("my_notebook.ipynb", "r") as f:
    blob_client.upload_blob(f.read(), overwrite=True)

# 3. 发送 ServiceBus 消息
message = {
    "BlobId": blob_id,
    "Script": "_temp_run",
    "IncidentId": "0",
    "InputParametersJson": json.dumps({
        "ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev260413061005",
        "FORCE_REFRESH_NOTEBOOK_CACHE": True
    }),
    "SubmittedBy": "ZeroToilLocalRun",
    "SubmitTime": datetime.utcnow().isoformat(),
}
sender.send_messages(ServiceBusMessage(json.dumps(message)))
```

前提条件:
- ServiceBus 连接字符串（已在 `config.py` 中）
- `XJPLAzureStorageCredential`（pod 中或本地 `az login`）

#### 方案 B: 通过 XPortal API（和前端一致）

```python
import requests

XPORTAL = "https://xportal-aad.trafficmanager.net"
headers = {"Content-Type": "application/json", "Authorization": xportal_token}

# 1. SubmitAKSJob
resp = requests.post(f"{XPORTAL}/api/v1/XJupyterlite/SubmitAKSJob",
    headers=headers,
    json={
        "Script": "_temp_run",
        "InputParametersJson": '{"ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev260413061005"}',
        "SubmittedBy": "ZeroToilLocalRun",
    })
job_id = resp.json()["IncidentDiagnosticItemId"]

# 2. SavePickleObj
blob_id = f"{job_id}_temp_run"
with open("my_notebook.ipynb", "r") as f:
    requests.post(
        f"{XPORTAL}/api/v1/XJupyterlite/SavePickleObj?storageId={blob_id}",
        headers=headers,
        data=f.read(),
    )
```

前提条件:
- xportal API token（从 KeyVault 获取，和 `run_job_locally.py` 中 `TokenRefresher` 相同）

### 对比

| 方面 | 方案 A (ServiceBus) | 方案 B (XPortal API) |
|---|---|---|
| 认证 | ServiceBus 连接字符串 + Storage credential | xportal token |
| 复杂度 | 需要直接操作 blob + ServiceBus | 两个 HTTP POST |
| 已有参考 | `run_job_locally.py` | 前端 `handler.ts` |
| 适用场景 | 已有 ServiceBus 访问 | 没有直接 ServiceBus 访问 |

### 结论

**可以在本地做同样的事情。** `run_job_locally.py` 已经实现了 80% 的功能，
只需要额外增加：
1. 读取本地 notebook 文件
2. 上传到 `xjupyterlite-pythonobj` blob container（blob name = `{job_id}_temp_run`）
3. 把 ServiceBus 消息的 `Script` 改为 `"_temp_run"`，`BlobId` 改为 `{job_id}_temp_run`
