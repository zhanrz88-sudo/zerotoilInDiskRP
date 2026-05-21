# ZeroToil 用户调用指南

## 概述

ZeroToil 让你可以在 XJupyterLite notebook 执行时自动加载 AI 生成的
Python 包。你只需要在提交 notebook job 时设置 `InputParametersJson`
中的参数即可。

---

## 参数说明

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `ZEROTOIL_PACKAGE_VERSION` | string | 是 | 要安装的包版本号 |
| `ZEROTOIL_USE_OFFICIAL` | bool | 否 | 在 Test/Stage 中强制使用 official 包（默认 `false`） |

---

## 版本号格式

有两种包，对应两种版本号格式：

| 包 | 版本格式 | 示例 | 发布者 |
|---|---|---|---|
| `zerotoil` (dev) | `0.0.1.dev<YYMMDDHHMMSS>` | `0.0.1.dev260415033907` | 开发者本地脚本 |
| `zerotoil-official` (prod) | `0.0.0.N` | `0.0.0.3` | 官方 CI pipeline |

系统会 **自动根据版本号格式** 判断安装哪个包，你不需要手动指定包名。

---

## Stage / Test 环境调用示例

### 1. 使用自己 build 的 dev 包

最常用的场景 — 开发调试阶段，使用自己上传的版本：

```json
{
  "ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev260415033907"
}
```

效果：`pip install zerotoil==0.0.1.dev260415033907`

### 2. 使用最新的 dev 包

不指定具体版本，安装 feed 中最新的 dev 包：

```json
{
  "ZEROTOIL_PACKAGE_VERSION": "latest"
}
```

效果：`pip install zerotoil`（pip 自动选最新版本）

### 3. 使用特定 official 版本（预发布验证）

在 Test/Stage 中测试即将上 Prod 的 official 版本：

```json
{
  "ZEROTOIL_PACKAGE_VERSION": "0.0.0.3",
  "ZEROTOIL_USE_OFFICIAL": true
}
```

效果：`pip install zerotoil-official==0.0.0.3`

> **注意**：`ZEROTOIL_USE_OFFICIAL` 只在 Test/Stage 中需要显式设置。
> 如果不设置且版本号是 `0.0.0.N` 格式，系统也会自动识别为 official 包。

### 4. 使用 official 版本（自动识别，无需 USE_OFFICIAL）

系统可以根据版本号格式自动识别：

```json
{
  "ZEROTOIL_PACKAGE_VERSION": "0.0.0.3"
}
```

效果：自动识别为 official → `pip install zerotoil-official==0.0.0.3`

### 5. 使用最新 official 包

```json
{
  "ZEROTOIL_PACKAGE_VERSION": "latest",
  "ZEROTOIL_USE_OFFICIAL": true
}
```

效果：`pip install zerotoil-official`（最新 official 版本）

### 6. 不使用 ZeroToil

不设置 `ZEROTOIL_PACKAGE_VERSION`，或者不包含在参数中：

```json
{
  "FORCE_REFRESH_NOTEBOOK_CACHE": true
}
```

效果：不安装任何 zerotoil 包，notebook 正常执行。

---

## Prod 环境

Prod 环境 **只能使用 official 包**，dev 版本会被直接拒绝。

```json
// ✅ Prod 允许
{"ZEROTOIL_PACKAGE_VERSION": "0.0.0.3"}

// ✅ Prod 允许
{"ZEROTOIL_PACKAGE_VERSION": "latest"}

// ❌ Prod 拒绝 — RuntimeError
{"ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev260415033907"}
```

---

## 完整决策表

| 环境 | 版本参数 | `USE_OFFICIAL` | 实际安装 |
|---|---|---|---|
| Stage | `0.0.1.dev260415033907` | — | `zerotoil==0.0.1.dev260415033907` |
| Stage | `0.0.0.3` | — | `zerotoil-official==0.0.0.3` (自动识别) |
| Stage | `0.0.0.3` | `true` | `zerotoil-official==0.0.0.3` |
| Stage | `latest` | — | `zerotoil` (最新 dev) |
| Stage | `latest` | `true` | `zerotoil-official` (最新 official) |
| Stage | — | — | 不安装 |
| Prod | `0.0.0.3` | — | `zerotoil-official==0.0.0.3` |
| Prod | `latest` | — | `zerotoil-official` (最新) |
| Prod | `0.0.1.dev...` | — | ❌ 拒绝 |

---

## 如何获取版本号

### Dev 版本

运行 `run_zerotoil_job.py` 脚本时会自动生成并输出版本号：

```
[zerotoil] Published version: 0.0.1.dev260415033907
```

### Official 版本

```bash
# 查看最新 official 版本
cat zero-toil/LATEST_OFFICIAL_VERSION

# 或在 ADO feed 中搜索
pip index versions zerotoil-official \
  --index-url https://msazure.pkgs.visualstudio.com/One/_packaging/Storage-XI-feed/pypi/simple/
```

---

## 通过 XPortal API 提交 (Python)

```python
from xportal import submit_template_job

# 使用自己的 dev 版本
job_id = await submit_template_job(
    "/Xstore/Developer/myalias/my-notebook.ipynb",
    parameters={
        "ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev260415033907",
    },
)

# 使用 official 版本做预发布测试
job_id = await submit_template_job(
    "/Xstore/Developer/myalias/my-notebook.ipynb",
    parameters={
        "ZEROTOIL_PACKAGE_VERSION": "0.0.0.3",
        "ZEROTOIL_USE_OFFICIAL": True,
    },
)
```

---

## 通过 run_job_locally.py 提交

修改 `run_job_locally.py` 中的 `params`：

```python
params = json.dumps({
    "ZEROTOIL_PACKAGE_VERSION": "0.0.1.dev260415033907",
    "FORCE_REFRESH_NOTEBOOK_CACHE": True,
})
```

---

## FAQ

**Q: 我上传了一个 dev 版本但 notebook 里 `import zerotoil` 报错？**

检查版本号是否正确：`0.0.1.dev` 后面必须是 12 位数字
（YYMMDDHHMMSS），例如 `0.0.1.dev260415033907`。

**Q: Stage 可以用 official 包吗？**

可以。设置 `ZEROTOIL_USE_OFFICIAL: true`，或者直接用 `0.0.0.N` 格式的
版本号（系统会自动识别）。

**Q: Prod 可以用 dev 包吗？**

不可以。Prod 只接受 `0.0.0.N` 格式或 `latest`。给 dev 版本号会直接
返回 `RuntimeError`，job 状态变为 `FailedJobSubmission`。

**Q: `latest` 在不同环境下行为不同吗？**

是的。
- Stage（默认）：安装最新 `zerotoil`（dev 包）
- Stage + `USE_OFFICIAL=true`：安装最新 `zerotoil-official`
- Prod：总是安装最新 `zerotoil-official`
