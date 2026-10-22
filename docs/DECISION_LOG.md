# Decision Log

This records design choices, not deployed features.

| ID | Date | Decision | Rationale / tradeoff |
| --- | --- | --- | --- |
| D-001 | 2026-10-22 | Build a **personal-use**, single-owner application first | Avoid multi-tenant/auth complexity; learn from actual use |
| D-002 | 2026-10-22 | Xano backend selected; frontend choice deferred | WeWeb is an option, and a coded application hosted on Vercel is also under consideration; avoid premature frontend commitment |
| D-003 | 2026-10-22 | Ten business tables in V1 | Enough to preserve customer → evidence → insight → hypothesis → experiment |
| D-004 | 2026-10-22 | Manual interviews and survey input first | Avoid premature ingestion/automation |
| D-005 | 2026-10-22 | Store survey wave and segment snapshots | Protect historical interpretation and cohort comparisons |
| D-006 | 2026-10-22 | PMF denominator = valid respondents; 40% is only a heuristic | Avoid false precision and mistaken PMF claims |
| D-007 | 2026-10-22 | Raw evidence separate from analyzed insights | Traceability; corrections and counterevidence |
| D-008 | 2026-10-22 | Claude Code may use MCP only after inspection; no writes/publish without approval | Prevent accidental changes to wrong workspaces |
| D-009 | 2026-10-22 | Xano auth infrastructure is outside the ten business tables | Clarifies scope rather than pretending auth is optional |
| D-010 | 2026-10-22 | Product event telemetry, billing, organizations and AI recommendations are deferred | Keep implementation small, meaningful and testable |
| D-011 | 2026-10-22 | User created a Xano workspace named `pmf`; inspect it first | Workspace existence reported by owner; actual workspace ID, branch and schema still require read-only verification |
| D-012 | 2026-10-22 | Postpone frontend decision until backend specifications/APIs are established | The data architecture and API contracts should remain frontend-independent |

| D-013 | 2026-10-22 | Owner account reported created and auth endpoints working | User reported completion; owner numeric ID and public signup lockdown still require verification |
| D-014 | 2026-10-22 | Start Phase 2 with Market tables only: `products`, `segments`, `customers` | Smallest practical batch for the core domain; CLI push remains disabled pending a scoped review |

## Open technical decisions
Not yet decided: Xano physical field types/constraints; actual Xano branch; frontend choice and, if Vercel, frontend framework; API naming; referential deletion semantics; finalized authentication policy; backup and release mechanism. Resolve after read-only environment inventory. Mark updates here with dated decisions and supporting test or rationale.
