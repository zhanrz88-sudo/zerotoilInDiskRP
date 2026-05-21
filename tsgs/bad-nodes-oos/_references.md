# Shared References — Bad Nodes Out of Service

## Geneva Actions

### Quarantine (Short Term)

| Name | OperationId | Breadcrumb |
|---|---|---|
| Quarantine Role Instances | `QuarantineRoleInstancesDelegated` | `Xstore > Sustainability Operations With Delegated Auth - Safe > Quarantine Role Instances With Delegated Auth` |
| Un-Quarantine Role Instances | `UnQuarantineRoleInstancesDelegated` | `Xstore > Sustainability Operations With Delegated Auth - Safe > UnQuarantine Role Instances With Delegated Auth` |
| Get Quarantine Status | `GetQuarantineStatusDelegated` | `Xstore > Sustainability Operations With Delegated Auth - Safe > Get Quarantine Status With Delegated Auth` |

### OOS Role Marker (Medium Term)

| Name | OperationId | Breadcrumb |
|---|---|---|
| Set RoleInstance OOS | `SetRoleInstanceOOSExternalWithSafetyChecksDelegated` | `Xstore > Sustainability Operations With Delegated Auth - Safe > Set RoleInstance to OOS External With Safety Checks And Delegated Auth` |
| Set RoleInstance In Service | `SetRoleInstanceInServiceWithSafetyChecksDelegated` | `Xstore > Sustainability Operations With Delegated Auth - Safe > Set Role Instance In Service With Safety Checks and Delegated Auth` |

### OOS via DC (Long Term)

| Name | OperationId | Breadcrumb |
|---|---|---|
| Take FE RoleInstance OOS Via DC | `TakeFERoleInstanceOOSViaDC` | `Xstore > XFE Operations > Take FE RoleInstance OOS Via DC` |

### MR Repair

| Name | OperationId | Breadcrumb |
|---|---|---|
| Request Repair (Reboot, ReimageOS, Repave, OFR) | `RequestRepairActionFromMRDelegated` | `Xstore > Sustainability Operations With Delegated Auth - Safe > Request Repair (Reboot, ReimageOS, Repave, OFR) With Delegated Auth` |

## JIT Access Requirements

| Resource Type | Instance | Access Level | When Required |
|---|---|---|---|
| XDS | `<tenant_name>` | Storage-PlatformServiceOperator | All steps (restart, quarantine, OOS) |
| XDS | `<tenant_name>` | Storage-DynamicConfigUpdateRole | Step 4 — OOS via DC (long term) |

Portal: [aka.ms/JIT](https://aka.ms/JIT)

For non-public clouds, see [aka.ms/jit](https://aka.ms/jit) for the right portal.

## DGrep Events

| Namespace | Event | Purpose | Key Fields |
|---|---|---|---|
| `Xstore` | `ServerStatsEx1` | Node health grades reported by Table Server | `TableServer`, `HealthGrade` (4=Healthy, 1=Unhealthy) |

### Health Grade Scale

| Grade | Meaning | Recommended Action |
|---|---|---|
| 4 | Healthy | Restart first, monitor for recovery |
| 3 | Degraded | Restart, monitor closely |
| 2 | Warning | Consider OOS if restart fails |
| 1 | Unhealthy | Take FE roles OOS |

## XDS Dynamic Config Paths (for OOS via DC)

| Role Type | Config Path |
|---|---|
| Native XFE | `XStoreConfigSettings/NativeXfe/Common/BackgroundSettings/SlbOutOfRotationInstanceIds` |
| Managed XFE (Blob) | `XStoreConfigSettings/BlobXfe/Settings/SlbProbeDownInstanceIds` |
| Managed XFE (Table) | `XStoreConfigSettings/TableXfe/Settings/SlbProbeDownInstanceIds` |
| Managed XFE (Queue) | `XStoreConfigSettings/QueueXfe/Settings/SlbProbeDownInstanceIds` |

## XDS Pages

| Page | Purpose |
|---|---|
| Tenant Status > Role Summary | View role instances, restart, request MR, set OOS |
| XML Dynamic Config > Configuration | View/edit DC settings for OOS via DC |
| Log File Explorer | Download role instance logs and .etl trace files |

## Portals

| Name | URL |
|---|---|
| Geneva Actions (SAW) | [portal.microsoftgeneva.com/actions](https://portal.microsoftgeneva.com/actions) |
| XDS Portal | XDS UX (tenant-specific, accessed via XPortal) |
| Azure Watson | Crash dump search |
| JIT Portal | [aka.ms/JIT](https://aka.ms/JIT) |

## Escalation Contacts

| Team | Contact | When |
|---|---|---|
| XFE Team | IcM — `One\XStore\XFE` | File follow-up bugs for bad node root cause |
| Resiliency Team | (internal docs) | CPU trace / profiling guidance |
| XSSE DRI (Public) | [IcM On-Call](https://portal.microsofticm.com/imp/v3/oncall/current?serviceId=10050&teamIds=42293) | Escalation if all OOS approaches fail |

## Automation Constraints

| Constraint | Details |
|---|---|
| SAW/dSTS required for mutating GAs | `StoragePlatformServiceViewer` cert (automation) can only run READ-ONLY actions |
| Automation pattern for mutating ops | Prepare parameters → generate Geneva Action portal link → human executes on SAW |
| XDS mutating APIs | `ManagementRoleApi` has `quarantine_role_instances()`, `request_repair()` etc. — gate behind approval |
