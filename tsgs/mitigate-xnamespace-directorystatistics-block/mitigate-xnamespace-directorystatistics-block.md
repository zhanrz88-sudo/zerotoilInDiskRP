# Mitigate XNamespaceDirectoryStatistics Block

> **Source**: [Failover blocked by XnamespaceDirectoryStatistics](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/Table_Layer/tsgs/Geo/Failover%20blocked%20by%20XnamespaceDirectoryStatistics.md&_a=preview)
> **Related**: [[FailoverPendingTransaction] Failover for accounts stuck on PrimaryStuck.PrepareFailover in XXX](https://msazure.visualstudio.com/One/_git/Storage-XStore-Docs?path=/Table_Layer/tsgs/Geo/%5BFailoverPendingTransaction%5D%20Failover%20for%20accounts%20stuck%20on%20PrimaryStuck.PrepareFailover%20in%20XXX.md&_a=preview)

## Purpose

Apply the known mitigation when failover is blocked at Primary-side PrepareFailover due to unpaired rows in `XNamespaceDirectoryStatistics`.

## Inputs

| Parameter | Type | Source |
|---|---|---|
| `tenant_name` | `str` | Calling TSG input |
| `versioned_account_name` | `str` | Derived from account context (`<account>\\x01<suffix>`) |
| `incident_id` | `int` | Calling TSG input |
| `environment` | `str` | Calling TSG input |

## Outputs

| Field | Type | Description |
|---|---|---|
| `ga_invocation_id` | `str` | Geneva action invocation id |
| `mitigation_executed` | `bool` | True when action executed successfully |
| `post_check_stage` | `str` | Stage observed after mitigation verification |

## Steps

### Step 1 — Confirm known signature in primary logs

[Step Analysis](steps/step-1-confirm-signature.md)

Query relevant XAC diagnostics around incident window and verify presence of error text:

`Table:XNamespaceDirectoryStatistics which has not done pairing has data`

If signature is absent, stop and route to escalation.

### Step 2 — Execute Geneva action

[Step Analysis](steps/step-2-execute-action.md)

Run action:
- Action group: `GeoHelper`
- Action: `clean up rows in new tables to unblock failover`
- Parameters: `Tenant = <tenant_name>`, `TableName = XNamespaceDirectoryStatistics`, `AccountName = <versioned_account_name>`

### Step 3 — Poll action result and verify progression

[Step Analysis](steps/step-3-verify-progression.md)

Wait for action completion. Re-run `AccountFailoverStatisticsEvent` query and confirm stage advanced past the Primary-side PrepareFailover block. Record outcome in incident thread.

## Automation Notes

```
CODING_ABILITY_DEPENDENCY: geneva-action-call (xportal.acis.submit, xportal.acis.get_result), dgrep-query (xportal.dgrep.query), icm-get-incident (Incident.add_description)
AUTOMATABLE: Partially (execution is technically automatable but requires human approval and a validated operation-id mapping for the Geneva action)
MANUAL_FALLBACK: Run the Geneva action manually from approved portal workflow, then re-check failover statistics and document results in ICM.
```

## Open Questions

| # | Question |
|---|---|
| 1 | What is the exact ACIS extension and `operation_id` for this GeoHelper action so it can be executed reliably via API? |
| 2 | Which role instance/log source should be the canonical automated source for signature confirmation: `XACServer` cosmos logs or DGrep mirrored events? |
