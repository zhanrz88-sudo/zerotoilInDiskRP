# DataBox DGrep patterns

These examples query DataBox copy job logs.

Namespaces: `DataBoxCopyRole`, `DataBoxDiag`
Events: `DataEvent`

## Example: DataBox copy job progress (MQL + client query)

```python
import datetime
from xportal import dgrep

tenant = "<databox_tenant>"  # e.g. the tenant from the incident

namespace = ["DataBoxCopyRole", "DataBoxDiag"]
event_name = "DataEvent"

scope_conditions = {
    "Tenant": [tenant],
    "Role": ["CopyRole"],
}

query = 'where Message.contains("JobId:")'
client_query = "orderby PreciseTimeStamp asc"

end_time = datetime.datetime.now(datetime.timezone.utc)
start_time = end_time - datetime.timedelta(minutes=10)

result = await dgrep.query(
    namespace,
    event_name,
    start_time,
    end_time,
    server_query=query,
    scope_conditions=scope_conditions,
    client_query=client_query,
)

# Get shareable link
dgrep_link = result.get_dgrep_link()
print(dgrep_link)

df = result.to_df()
```

Inspired by:
- jupyter-templates/DataBox/DataBoxPerformanceTriage.ipynb
- jupyter-templates/DataBox/generalTemplate.ipynb

## Notes

- DataBox queries use **multiple namespaces** (`DataBoxCopyRole` + `DataBoxDiag`).
- Scope conditions use `Tenant` and `Role` instead of `Moniker` (unlike XStore).
- `client_query` is useful for ordering results after retrieval.
