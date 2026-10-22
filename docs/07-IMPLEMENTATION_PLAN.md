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
