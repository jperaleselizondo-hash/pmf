# Project Status

**Date:** 2026-10-22
**Milestone:** Documentation foundation
**Product build:** User created Xano workspace `pmf`; schema/API work not started (workspace not yet inspected)
**Production:** No PMF Engine application deployed

## Completed / documented
- [x] Problem, target user and vision described
- [x] Verified original Y Combinator and Superhuman references
- [x] Seven-module operating logic and survey PMF formula specified
- [x] Initial 10-table logical relational model and integrity invariants recorded
- [x] Personal-use app flows, technical boundaries, test plan and phased roadmap drafted
- [x] Collaboration agreement for Claude Code / MCP authored

## Not started
- [ ] Phase 1: Read-only inventory of Xano workspace `pmf` and Claude MCP connectivity; defer frontend inspection
- [ ] Phase 2: Physical Xano schema
- [ ] Phase 3: Auth and market/customer/interview APIs
- [ ] Phase 4: Survey/report API and sample-cohort tests
- [ ] Phase 5: Insight/evidence/hypothesis/experiment APIs
- [ ] Phase 6: Choose frontend (WeWeb or coded app hosted on Vercel), then build screens and end-to-end workflow
- [ ] Phase 7: QA and approved publication

## One next action
Run the **Phase 1 read-only Claude reconnaissance prompt** in docs/07-IMPLEMENTATION_PLAN.md. Return its report for architectural review before approving any writes.

## Current risks
- The availability and scope of Xano MCP tools for Claude have not been verified; the `pmf` workspace name is user-provided, not independently inspected.
- The frontend has not been selected; Vercel is a deployment platform and requires a separate frontend implementation choice.
- Database-level cross-product referential integrity may require explicit API validation.
- Survey data alone does not prove retention, willingness to pay, or product-market fit.
- Real customer notes may contain personal information; use synthetic fixtures for development.

## Update policy
Only mark a phase complete when the corresponding real system change is evidenced by inspection/tests. Commit this file alongside durable implementation decisions; distinguish local draft, development, production, and frontend publication state.
