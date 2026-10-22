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
| D-015 | 2026-10-22 | Market tables applied to `pmf` (ID 2) branch `v1` via temporary direct CLI push: dry-run → user-run interactive partial push → push disabled → read-back | Verified: exactly 3 tables created, existing `user`/auth resources byte-identical, server schema matches `xano/market/table/*.xs`; `allow_push` back to false |
| D-016 | 2026-10-22 | Git `xano/` XanoScript files are the schema source of truth and keep server-assigned `guid` lines | GUIDs let later partial pushes target the same tables instead of creating duplicates; server-side formatting differences (description→comment) are cosmetic |
| D-017 | 2026-10-22 | Market physical schema conventions: plural table names; `text? x?` for nullable optional fields; `int … { table = … }` references (metadata only); `created_at?=now` and API-maintained `updated_at`; case-sensitive unique segment names; `sensitive=true` on customer `name`/`email` | Native Xano constructs confirmed by validator and server dry-run; integrity beyond types/enums/unique indexes is enforced in APIs |
| D-018 | 2026-10-22 | Research survey `started_at` nullable | Permit wave draft creation; API requires start before any survey response |
| D-019 | 2026-10-22 | Interview `notes` nullable | Transcript or alternatives/problem context may be original evidence; require meaningful content before citation |
| D-020 | 2026-10-22 | Raw interview and survey answers remain untrimmed | Preserve first-hand wording; trim survey configuration fields instead |
| D-021 | 2026-10-22 | Closed wave is read-only; explicit reopening required for corrections | Preserve a stable measurement window; no assertion of an audit log until implemented |
| D-022 | 2026-10-22 | Category without `responded_at` invalid; `responded_at` without category allowed as partial | Separate survey participation from valid PMF denominator; report incomplete responses |
| D-023 | 2026-10-22 | Do not enforce unique `survey_waves(product_id, name)` | Stable wave ID distinguishes repeated survey names |
| D-024 | 2026-10-22 | Research tables applied to `pmf` (ID 2) branch `v1`: dry-run (3 CREATEs) → user-run interactive partial push → push disabled → read-back; server GUIDs committed | Verified: 9 pre-existing definitions byte-identical, Research schema matches `xano/research/table/*.xs`; `allow_push` confirmed false via CLI after a re-toggle |
| D-025 | 2026-10-22 | The push gate is closed only when the CLI reports `allow_push: false` | The UI toggle was once reported off while the CLI still showed true |

## Open technical decisions
Not yet decided: physical schema for the remaining seven business tables (Market conventions in D-017 are the default); dev/data-source isolation beyond live branch `v1`; frontend choice and, if Vercel, frontend framework; API naming; referential deletion semantics; finalized authentication policy; backup and release mechanism. Resolve after read-only environment inventory. Mark updates here with dated decisions and supporting test or rationale.
