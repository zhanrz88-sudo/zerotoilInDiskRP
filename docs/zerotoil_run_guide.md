# ZeroToil: Build, Publish & Run

## One-time Setup

```bash
pip install build twine keyring artifacts-keyring azure-servicebus
az login
```

Create `zero-toil/scripts/config.py` (gitignored) with your Service Bus connection string:
```python
CONNECTION_STRING = "Endpoint=sb://..."
```

## Run

```bash
cd zero-toil

# Build → Publish to feed → Submit job to test queue
python scripts/run_zerotoil_job.py --environment test

# Reuse an already-published version (skip build & publish)
python scripts/run_zerotoil_job.py --version 0.0.1.dev260413061005 --environment test
```

The script will:
1. Build a wheel with a unique version (e.g. `0.0.1.dev260414093012`)
2. Publish it to [Storage-XI-feed](https://msazure.visualstudio.com/One/_artifacts/feed/Storage-XI-feed)
3. Submit a Service Bus message with `ZEROTOIL_PACKAGE_VERSION` in `InputParametersJson`
4. The worker runs `pip install zerotoil==<version>` then executes the notebook
