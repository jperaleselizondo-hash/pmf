# 07 — Implementation Sequence

## Approach
Use small vertical slices. Each phase has an observable acceptance gate. Do not confuse docs, schema creation, successful API test, frontend preview, and production release.

| Phase | Work | Acceptance gate |
| --- | --- | --- |
| 0 — Documentation | Idea, sources, logic, data model, spec and working agreement | All docs on GitHub; no claim of deployed app |
| 1 — Environment inspection | Confirm user-created Xano workspace `pmf`, actual ID/branch, accessible Xano MCP operations; inventory current state (no frontend inspection yet) | Read-only inventory and exact scoped build proposal |
| 2 — Physical Xano schema | Map 10 logical business tables to actual Xano types/relations/indexes, author fixtures and constraints | Schema inspected; no unintended data changes; relationships verified |
| 3 — Auth and foundational APIs | Owner login/authorization, products, segments, customers, interviews | Auth negative tests and CRUD pass |
| 4 — Research and PMF APIs | Survey waves, participations, response edits, validated PMF report with denominators | Duplicates/cross-product invalid; counts and N/A tests pass |
| 5 — Evidence / validation APIs | Insights, evidence provenance, hypotheses, experiments | Full evidence → experiment round-trip passes |
| 6 — Frontend MVP (technology TBD) | Choose WeWeb or coded frontend deployed on Vercel; build forms, detail pages and dashboard from Xano APIs | Owner completes one synthetic end-to-end scenario in preview |
| 7 — Release QA | Security, usability, empty/error states, backup/rollback, responsive checks | Approval to publish; smoke tests after publication |

## Immediate next task (Phase 1)
A **read-only** reconnaissance prompt for Claude Code in Cursor:

> Read PROJECT_CONTEXT.md, CLAUDE.md, docs/04-LOGICAL_DATA_MODEL.md, docs/06-TECHNICAL_ARCHITECTURE.md, and docs/PROJECT_STATUS.md. Inspect the Git baseline and discover the available Xano MCP tools. Find the user-created Xano workspace named `pmf` and report its observed workspace ID and development/live branch state; do not assume that a similarly named workspace is the intended one without confirming its identity. Inventory existing tables, API groups, and potential naming conflicts (the workspace may be empty). Without making changes, propose a minimal physical Xano schema for the ten business tables: field types, references, indexes/uniqueness, validation and authorization strategy, native constraints versus API-enforced invariants, and safe order of creation. Include how Xano authentication infrastructure fits outside the ten domain tables. Identify risks, missing permissions and exact approvals needed. **Read-only only:** do not create/edit tables, records, auth, API endpoints, credentials, branches, frontend projects, or publish anything. Frontend choice between WeWeb and Vercel-hosted code is deferred.

## Phase 1 follow-up: unblock access (2026-10-22)
Claude's initial read-only report confirms the PMF Git baseline but could not inspect `pmf`: no Xano Developer MCP was active in that Claude Code session. An apparent global Cursor MCP config is **not** proof that Claude Code has that connection.

**Important tool distinction:** `@xano/developer-mcp` documents XanoScript/Meta API/CLI and validates code; it does not by itself authenticate Claude into a live workspace. Use Xano CLI or authenticated Metadata API to inspect actual workspaces, after selecting an explicit profile for `pmf`. Official references: https://github.com/xano-inc/xano-developer-mcp and https://github.com/xano-inc/cli.

1. Register the Developer MCP for the PMF Claude Code project only, if desired, and verify `claude mcp list` in that context. Restart the Claude session to load new connections.
2. Use Xano CLI (or authorized equivalent) with owner-approved authentication. Establish a **distinct `pmf` profile**; never rely on global default workspace or reuse a Goodz profile implicitly. Never print credentials or commit token-bearing files.
3. Read-only: list workspaces; identify `pmf` by name and observed ID; list its branches; inspect schema/auth/API inventory using explicitly targeted workspace/profile arguments.
4. Revisit physical schema proposals, especially native type/index support, evidence source fields, owner ID and deletion/review invariants. Report verified capabilities vs assumptions; request authorization before any data/schema/branch mutation.

## Phase 1 verified inventory and auth preflight (2026-10-22)
Claude verified via CLI with `-p pmf -w 2`: workspace **pmf** ID **2** on instance `xgjc-aodb-3a7q`; one live branch `v1`; only table `user` and Authentication API endpoints `auth/login`, `auth/me`, and public `auth/signup`. `allow_push` is disabled. User rows, owner identity, additional data-source environments, and permissions to disable signup were not inspected.

**First milestone before schema writes (Batch 0):** confirm the owner account by inspecting user count/identity through a suitably limited administrative view without exposing password data; create owner account only if needed and separately authorized; verify owner login and `auth/me`; disable `auth/signup` **external access** (prefer reversible disabling over deleting). Confirm failed public signup and successful owner login. Do not expose secrets in terminal output or commit them.

**Important owner guard:** `products.owner_user_id` is useful but insufficient to restrict a product to one person: any separately authenticated account could otherwise create its own product. Enforce a single designated owner user ID at the start of **every** PMF business endpoint, *plus* record ownership/product integrity checks. Existing unauthorized user rows or tokens must not gain access.

**Schema strategy:** Keep physical schema on hold until auth preflight and explicit approval. Xano docs say API branches isolate business logic, not a separate dataset; Data Source Environments may separate records but share schema (availability to be checked). `allow_push` enabling is a **critical** CLI operation and is not automatically authorized; consider UI table creation versus tightly scoped CLI push with dry-run and diff after owner approval. Avoid records/env/truncate/sync-delete/force options.

**Provisional schema review:** favor D1 and D2, D4 through D8, but **do not convert `insight_evidence.source_field` to an enum** without a compelling reason; validated text is more extensible. These are recommendations, not recorded approvals.

## Phase 2 design choices to settle after inspection
- Xano ID/reference field types and naming conventions.
- Owner auth identity, private data access pattern and permission enforcement.
- Physical treatment of enum values, timestamps and nullable fields.
- Cross-product references: database-level options vs Xano API validation.
- Safe deletion strategy for referenced evidence.
- Where to compute report aggregations and validation checks.
- Backup strategy and choice of synthetic seed data.

## Slice size guidance
Prefer schema one domain at a time (Market → Research → Intelligence → Validation), with read-only diff and approval between mutations. APIs should follow the same order. Choose the frontend later, once the corresponding backend read/write contract passes tests; Vercel hosting requires a separate frontend framework/codebase choice.

## Release readiness criteria
- Data integrity tests pass.
- Auth protects all endpoints and client-side routes.
- Report calculations match known fixtures.
- All create/read/update flows and linked navigation work.
- Cross-product access is denied, even when submitting forged IDs.
- Original evidence is preserved and referenced.
- Documentation accurately records actual Xano/frontend versions/resources, test outcomes, and rollback.

## Post-MVP backlog (not current scope)
Product events; true retention and value-event reporting; organizations; revenue and billing; AI-assisted qualitative classification; experiment statistical analysis; automated survey invitations; audit trail and multi-user controls.

## Hand-off convention
Every session ends with: baseline, scope, observed modifications, validation evidence, remaining risks, deployment/commit status, next one-step prompt. Update PROJECT_STATUS and DECISION_LOG only with verified changes and explicitly approved decisions.
