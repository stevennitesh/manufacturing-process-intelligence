# Triage labels

Map these roles to repository tracker values. The mapping supplies vocabulary;
the consuming workflow defines readiness criteria and permitted transitions.
Direct coding does not require a tracker item.

## Category roles

| Role | GitHub label |
| --- | --- |
| `bug` | `bug` |
| `enhancement` | `enhancement` |

## State roles

| Role | GitHub label |
| --- | --- |
| `needs-triage` | `needs-triage` |
| `needs-info` | `needs-info` |
| `ready-for-agent` | `ready-for-agent` |
| `ready-for-human` | `ready-for-human` |
| `implemented` | `implemented` |
| `wontfix` | `wontfix` |

At bootstrap, GitHub already had `bug`, `enhancement`, and `wontfix`. The other
state labels are mapped locally but were not provisioned remotely. Verify current
label availability before an operation needs it; provision missing labels only
when that external mutation is authorized.

A state label alone does not prove completion or remove an unresolved dependency.
