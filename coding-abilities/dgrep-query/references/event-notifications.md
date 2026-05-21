# Event Grid / notification DGrep patterns

These examples query XStore event grid notification traces.

Namespace: `Xstore`
Events: `ChangeNotificationTrace`, `XnsNotificationTrace`

## Example: Event Grid change notification trace

```python
import datetime
from xportal import dgrep
from xstore import get_tenant

tenant_name = "<tenant_name>"
account = "<account_name>"
container = "<container_name>"

tenant_entity = await get_tenant(tenant_name)
scope_conditions = {"Moniker": f"MdsXstore{tenant_entity.Moniker}"}

end_time = datetime.datetime.now(datetime.timezone.utc)
start_time = end_time - datetime.timedelta(minutes=5)

# Query for change notification events on a specific container
event_change_notification_trace = await dgrep.query(
    "Xstore",
    "ChangeNotificationTrace",
    start_time,
    end_time,
    server_query=f'where Account == "{account}" and Container == "{container}"',
    scope_conditions=scope_conditions,
)

event_change_notification_trace.show()
```

## Example: XNS notification trace

```python
xns_notification_trace = await dgrep.query(
    "Xstore",
    "XnsNotificationTrace",
    start_time,
    end_time,
    server_query=f'where Account == "{account}" and Container == "{container}"',
    scope_conditions=scope_conditions,
)

xns_notification_trace.show()
```

Inspired by:
- jupyter-templates/Xstore/XTable/EventGridNotificationTsg.ipynb
