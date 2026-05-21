# Step 1 — Verify network connectivity and SAC responsiveness

> **Parent TSG**: [fc-8-node-recovery](../fc-8-node-recovery.md)
> **Maps to**: `_step_1_verify_connectivity()` method

## Purpose
Check if the node is reachable on the network and responsive via SAC before attempting recovery.

## Inputs
| Parameter | Type | Source |
|---|---|---|
| `node_id` | `str` | TSG input |

## Outputs
| Field | Type | Description |
|---|---|---|
| `network_ok` | `bool` | Port enabled and link connected |
| `sac_responsive` | `bool` | SAC prompt appeared |
| `ip_ok` | `bool` | Non-APIPA IP address |
| `channels_ok` | `bool` | All expected channels present |

## Processing Logic
1. DCM Explorer → Resource Details → Operations → Network: Query `Port Isolation State` and `Link Active State`.
2. If Port disabled → Enable. If Link disconnected → send to OFR.
3. DCM Explorer → SAC tab → Connect → wait for `SAC>` prompt.
4. `SAC> i` — check IPs. APIPA (169.x) → skip to MOS recovery.
5. `SAC> ch` — check channels (SAC, PfAgent, Dcm). Missing → reboot → recheck.

## Automation Assessment
```
CODING_ABILITY_DEPENDENCY: None (DCM Explorer UI operations — no known programmatic API)
AUTOMATABLE: No (SAC and DCM Explorer are interactive tools)
MANUAL_FALLBACK: DRI uses DCM Explorer directly.
```

## Open Questions
| # | Question |
|---|---|
| 1 | Can DCM Explorer operations (port query, SAC connect) be automated via API? |
