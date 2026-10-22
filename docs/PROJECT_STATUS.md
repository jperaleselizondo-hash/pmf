# Project Status

**Date:** 2026-10-22
**Milestone:** Phase 1 workspace inspection verified; auth preflight next
**Product build:** Xano workspace `pmf` (ID 2) inspected by Claude; no PMF business tables, APIs or frontend implemented
**Production:** No PMF Engine application deployed

## Completed / documented
- [x] Problem, target user and vision described
- [x] Verified original Y Combinator and Superhuman references
- [x] Seven-module operating logic and survey PMF formula specified
- [x] Initial 10-table logical relational model and integrity invariants recorded
- [x] Personal-use app flows, technical boundaries, test plan and phased roadmap drafted
- [x] Collaboration agreement for Claude Code / MCP authored

## Not started
- [x] Phase 1: Read-only Xano CLI workspace inventory (Claude report received; no changes made); defer frontend inspection
- [ ] Phase 2: Physical Xano schema
- [ ] Phase 3: Auth and market/customer/interview APIs
- [ ] Phase 4: Survey/report API and sample-cohort tests
- [ ] Phase 5: Insight/evidence/hypothesis/experiment APIs
- [ ] Phase 6: Choose frontend (WeWeb or coded app hosted on Vercel), then build screens and end-to-end workflow
- [ ] Phase 7: QA and approved publication

## Phase 1 report received (2026-10-22)
- Claude verified clean local `main` at `c94cd4f` and found no active Xano MCP in this PMF Claude Code session.
- Reported Xano developer MCP configuration elsewhere (global Cursor and Goodz-specific Claude Code), not available within the PMF Claude session.
- Workspace ID, live/dev branch, existing tables, APIs and authentication remain **unverified**. No Xano, frontend or repository changes were made by Claude.
- Claude drafted candidate physical field types and constraints, but these have **not** been tested against the `pmf` workspace. Treat them as proposals, not accepted schema decisions.
- Official Xano docs distinguish the Developer MCP (docs/code validation) from authenticated workspace access, which is available through Xano CLI/Metadata API. Configuration must target `pmf`, not Goodz.

## Second Phase 1 verification (Claude report, 2026-10-22)
- Claude used CLI arguments `-p pmf -w 2` to confirm Xano instance `xgjc-aodb-3a7q`, workspace **pmf** (ID **2**), one live branch **v1**, and workspace `allow_push: false`.
- Workspace contains only authentication starter table `user` and API group `Authentication` with `auth/login`, `auth/me`, and **public live `auth/signup`**. No other tables, API groups, functions or tasks reported.
- User-row existence and owner identity were **not checked**. Do not assume an owner login exists, and do not retrieve passwords/hashes.
- Claude's initial physical schema and decisions D1–D8 remain **proposals**, not user-approved implementation changes.
- Xano officially distinguishes API branches (business-logic versions) from Data Source Environments (record separation). No isolated data source was verified for pmf.
- No Xano resources, Git files or frontend resources were modified during Claude's verification.

## Batch 0 preflight follow-up (2026-10-22)
- Claude confirmed group `Authentication`, with externally reachable `auth/login` and `auth/signup`, and authenticated `auth/me`. Unauthenticated `auth/me` returned 401. Owner user count/identity remain unverified.
- Claude incorrectly suggested that the endpoint must be deleted. **Official Xano Security / Pre-Launch docs document per-endpoint Settings → External Access.** Preferred remediation: verify owner login, then disable External Access on `auth/signup` and confirm public requests are blocked while login/me continue to function. Deletion is **not** approved.
- Owner identity should be confirmed manually in Xano `pmf` → Database → `user`, without exporting hashes or tokens. If there are no records, establish one authorized owner and verify login *before* blocking signup.
- Claude's local Git report said `c94cd4f`; GitHub's actual `main` was verified at `b2205c8` before this documentation update. Resolve remote and branch divergence before Claude commits.
- A future designated-owner check must protect every business endpoint; `products.owner_user_id` alone does not prevent another authenticated identity from creating products.
- **No application changes have been authorized or performed.** Record-only status update.

## One next action
Confirm user-row count and owner identity in Xano's UI, then verify owner login. After that, separately authorize disabling **External Access** on the `auth/signup` endpoint. Do not delete it. Fix Claude's local Git sync before committing documentation. Do not enable CLI push or create business tables yet.

## Approved-stack status
Xano selected; frontend still undecided between WeWeb and a coded frontend deployed on Vercel.

## Current risks
- Live public signup must be locked after owner login is established; future APIs must also reject **all non-owner auth identities** (data-level owner IDs alone do not enforce a single-user application).
- Xano CLI `allow_push` is disabled. Enabling it is explicitly flagged as critical by the CLI; requires separate approval and dry-run safeguards.
- Always specify CLI profile `pmf` and workspace 2, never depend on the default profile; the Goodz instance is shared.
- The frontend has not been selected; Vercel is a deployment platform and requires a separate frontend implementation choice.
- Database-level cross-product referential integrity may require explicit API validation.
- Survey data alone does not prove retention, willingness to pay, or product-market fit.
- Real customer notes may contain personal information; use synthetic fixtures for development.

## Update policy
Only mark a phase complete when the corresponding real system change is evidenced by inspection/tests. Commit this file alongside durable implementation decisions; distinguish local draft, development, production, and frontend publication state.
