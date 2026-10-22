# 07 — Implementation Sequence

## Approach
Use small vertical slices. Each phase has an observable acceptance gate. Do not confuse docs, schema creation, successful API test, WeWeb preview, and production release.

| Phase | Work | Acceptance gate |
| --- | --- | --- |
| 0 — Documentation | Idea, sources, logic, data model, spec and working agreement | All docs on GitHub; no claim of deployed app |
| 1 — Environment inspection | Confirm Xano workspace/development branch, WeWeb project, available MCP operations; inventory current state | Read-only inventory and exact scoped build proposal |
| 2 — Physical Xano schema | Map 10 logical business tables to actual Xano types/relations/indexes, author fixtures and constraints | Schema inspected; no unintended data changes; relationships verified |
| 3 — Auth and foundational APIs | Owner login/authorization, products, segments, customers, interviews | Auth negative tests and CRUD pass |
| 4 — Research and PMF APIs | Survey waves, participations, response edits, validated PMF report with denominators | Duplicates/cross-product invalid; counts and N/A tests pass |
| 5 — Evidence / validation APIs | Insights, evidence provenance, hypotheses, experiments | Full evidence → experiment round-trip passes |
| 6 — WeWeb MVP | Private layout, forms and detail pages, dashboard from backend reports | Owner completes one synthetic end-to-end scenario in preview |
| 7 — Release QA | Security, usability, empty/error states, backup/rollback, responsive checks | Approval to publish; smoke tests after publication |

## Immediate next task (Phase 1)
A **read-only** reconnaissance prompt for Claude Code in Cursor:

> Read PROJECT_CONTEXT.md, CLAUDE.md, docs/04-LOGICAL_DATA_MODEL.md, docs/05-MVP_WEB_APP.md, and docs/PROJECT_STATUS.md. Inspect Git state and discover currently available Xano and WeWeb MCP tools. Without making changes, identify the intended Xano workspace, any development branch, WeWeb project, relevant existing tables and API groups, and possible naming conflicts. Propose a scoped physical schema for the ten business tables with field types, relationships, indexes, constraint mechanisms, and safe execution order. Explicitly identify any logical invariants that Xano cannot enforce natively. Report blockers and the exact approvals needed; do not write schemas, APIs, workflows, data, or publish anything.

## Phase 2 design choices to settle after inspection
- Xano ID/reference field types and naming conventions.
- Owner auth identity, private data access pattern and permission enforcement.
- Physical treatment of enum values, timestamps and nullable fields.
- Cross-product references: database-level options vs Xano API validation.
- Safe deletion strategy for referenced evidence.
- Where to compute report aggregations and validation checks.
- Backup strategy and choice of synthetic seed data.

## Slice size guidance
Prefer schema one domain at a time (Market → Research → Intelligence → Validation), with read-only diff and approval between mutations. APIs should follow the same order. Build WeWeb once the corresponding backend read/write contract passes tests.

## Release readiness criteria
- Data integrity tests pass.
- Auth protects all endpoints and client-side routes.
- Report calculations match known fixtures.
- All create/read/update flows and linked navigation work.
- Cross-product access is denied, even when submitting forged IDs.
- Original evidence is preserved and referenced.
- Documentation accurately records actual Xano/WeWeb versions/resources, test outcomes, and rollback.

## Post-MVP backlog (not current scope)
Product events; true retention and value-event reporting; organizations; revenue and billing; AI-assisted qualitative classification; experiment statistical analysis; automated survey invitations; audit trail and multi-user controls.

## Hand-off convention
Every session ends with: baseline, scope, observed modifications, validation evidence, remaining risks, deployment/commit status, next one-step prompt. Update PROJECT_STATUS and DECISION_LOG only with verified changes and explicitly approved decisions.
