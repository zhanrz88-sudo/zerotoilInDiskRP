# Config, Scrubber & Partition Geneva Actions (Validated)

All examples below are taken directly from existing jupyter-templates with real `acis.execute()` or `acis.submit()` calls.

## Example: Trigger Scrubber on a partition (acis.execute)

```python
from xportal import acis

ACIS_EXTENSION_NAME = 'Xstore'
ACIS_OPERATION_ID = 'TriggerScrubber'

tenant_name = "<tenant_name>"
partition = "<partition_name>"  # Stream name

result = await acis.execute(
    ACIS_EXTENSION_NAME,
    ACIS_OPERATION_ID,
    [
        tenant_name,
        partition,   # Stream Name
        '',          # Start Key
        '',          # End Key
        'ValidateBlobExtent:false,ValidateHTBBLinkRecords:true,ValidatePageBlobExtent:true,ValidateBlockBlobExtent:true'
    ]
)
# Result contains 'resultMessage' with JSON payload including 'TaskId'
```

Source: jupyter-templates/Xstore/XTable/XBlob/WGDataIntegrityViolationXblocksChunkExtentMissingRunbook.ipynb

## Example: Run XDiag CmdLet — partition operation (acis.execute)

```python
import json
from xportal import acis

Tenant = "<tenant_name>"
MetadataStreamName = "<metadata_stream_name>"
Operation = "<operation>"  # e.g. "GetPartitionInfo"
RowKey = "<row_key>"

result = await acis.execute(
    'Xstore',
    'RunXDiagCmdLet',
    [
        'Invoke-XdsPartition',
        Tenant,
        json.dumps([
            ['MetadataStreamName', MetadataStreamName],
            ['Operation', Operation],
            ['RowKey', RowKey],
        ]),
    ],
)
```

Source: jupyter-templates/Xstore/XTable/GC/PartitionOperations.ipynb

## Example: Run XDiag CmdLet — key range blob GC bypass (acis.execute)

```python
import json
from xportal import acis

Tenant = "<tenant_name>"
BypassOperation = "<bypass_operation>"
LowKey = "<low_key>"
HighKey = "<high_key>"

result = await acis.execute(
    'Xstore',
    'RunXDiagCmdLet',
    [
        'Start-XdsKeyRangeBlobGCBypass',
        Tenant,
        json.dumps([
            ['BypassOperation', BypassOperation],
            ['LowKey', LowKey],
            ['HighKey', HighKey],
        ]),
    ],
)
```

Source: jupyter-templates/Xstore/XTable/GC/KeyRangeBlobGCBypass.ipynb

## Example: Config change — async submit + poll (acis.submit + acis.get_result)

```python
from xportal import acis

params = ["<config_params>"]  # Actual params vary by operation

response = await acis.submit(
    "Xstore",
    "XConfigImmediateManualOrchestration",
    params,
    endpoint="Production",
)
action_id = response["id"]
print(f"Geneva action submitted. ActionId={action_id}")

# Poll for result
import asyncio
for _ in range(30):
    try:
        result = await acis.get_result("Xstore", action_id)
        if result:
            print(f"Geneva action completed. Result: {result}")
            break
    except Exception:
        pass
    print("Geneva action still running...")
    await asyncio.sleep(10)
else:
    print("Geneva action did not complete before timeout.")
```

Source: jupyter-templates/Xstore/XTable/XBlob/LifespanPrediction/LifespanPredictionConfigUpdate.ipynb

## Example: Submit with confirmation gate (acis.submit — vacate automation)

```python
from xportal import acis

extension_name = "<extension_name>"
operation_id = "<operation_id>"
operation_params = ["<param1>", "<param2>"]

result = await acis.submit(
    extension_name,
    operation_id,
    operation_params,
    endpoint="Production",
)
# Track progress via Geneva Actions UI history tab
```

Source: jupyter-templates/Xstore/XTable/XBlob/RADecom/VacateAutomation.ipynb

## Example: acis.execute with auto-retry wrapper

```python
from xportal import acis

extension_name = "<extension_name>"
operation_id = "<operation_id>"
params = ["<param1>", "<param2>"]

# Some notebooks wrap acis calls with retry logic
result = await with_auto_retry(acis.execute, args=(extension_name, operation_id, params))
```

Source: jupyter-templates/Xstore/XTable/XBlob/DME/GC Based Rebalancing Anomaly Detector.ipynb

## Notes

- `TriggerScrubber` params: `[tenant_name, partition/stream_name, start_key, end_key, validation_options]`
- `RunXDiagCmdLet` params: `[cmdlet_name, tenant_name, json_encoded_params]` — the third param is always `json.dumps([[key, value], ...])`.
- Config operations are long-running — always use `acis.submit()` + `acis.get_result()` pattern.
- Several notebooks use custom retry wrappers around `acis.execute()` for resilience.
