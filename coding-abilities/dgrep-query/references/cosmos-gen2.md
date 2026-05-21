# Cosmos Store / Gen2 DGrep patterns

These examples query Cosmos Store Gen2 logs via DGrep.

Namespace: `Xstore`
Events: `NativeFePerfMetric`

## Example: Cosmos Store Gen2 DGrep with TagStorageStamp

```python
import datetime
from xportal import dgrep
from xstore.common.dgrep import get_moniker_by_xstore_tenant

tenant_name = "<tenant_name>"
moniker = await get_moniker_by_xstore_tenant(tenant_name)

# For Cosmos Store Gen2, use TagStorageStamp + Tenant
scope_conditions = {"TagStorageStamp": moniker, "Tenant": tenant_name}

namespace = "Xstore"
event_name = "NativeFePerfMetric"

query = 'where Status != "Success"'

end_time = datetime.datetime.now(datetime.timezone.utc)
start_time = end_time - datetime.timedelta(minutes=5)

result = await dgrep.query(
    namespace,
    event_name,
    start_time,
    end_time,
    server_query=query,
    scope_conditions=scope_conditions,
)

result.show()
```

## Example: Generate DGrep link without executing query

```python
dgrep_link = dgrep.get_dgrep_link(
    namespace, event_name,
    start_time, end_time,
    query,
    server_query_type="MQL",
    scope_conditions=scope_conditions,
)
print(dgrep_link)
```

Inspired by:
- jupyter-templates/Cosmos Store/SSS/Fetch Gen2 Dgrep Link.ipynb

## Notes

- For Cosmos Store, `TagStorageStamp` is used instead of `Moniker` in scope conditions.
- The `xportal.dgrep` implementation treats `TagStorageStamp` as a moniker when namespace is `Xstore`.
- `get_dgrep_link()` generates a parameterized Jarvis DGrep URL without executing the query.
