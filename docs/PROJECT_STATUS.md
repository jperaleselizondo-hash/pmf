# Project Status

**Date:** 2026-10-22
**Milestone:** Phase 2 Batch 2 Research schema prepared and offline-validated; not committed or applied (3 of 10 business tables live)
**Product build:** Xano workspace `pmf` (ID 2), branch `v1` (live): auth starter plus three empty Market tables; no business APIs, no records in business tables, no frontend
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
- [ ] Phase 2: Physical Xano schema — Batch 1 (Market: `products`, `segments`, `customers`) applied and verified; Research, Intelligence and Validation tables not started
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

## Owner account update (reported by user, 2026-10-22)
- User reports creating the PMF application owner account and successfully testing auth endpoints. The owner's numeric Xano user ID is **not** recorded here and must be verified locally through `auth/me` before future authorization logic is built.
- Public `auth/signup` **has not yet been confirmed disabled**. Lock down its **External Access** setting before business APIs are introduced; independently verify external rejection and successful owner login.
- User successfully synchronized local `pmf` repository with GitHub `main` at `f705787` before this update.
- User wants to proceed with table implementation. First target: `products`, `segments`, `customers`, schema only, no test data or business APIs. CLI `allow_push` remains off until a separate controlled authorization.

## Phase 2 Batch 1 report (Claude, 2026-10-22)
- Claude wrote only **scratchpad** XanoScript definitions: `products.xs`, `segments.xs`, `customers.xs`. All three passed offline syntax validation (Xano developer validator v2.2.6); files are **not in Git** or Xano yet.
- Intended indexes: `products.owner_user_id`; unique `segments(product_id,name)`; unique `customers(product_id,external_id)` plus additional lookup indexes.
- The local negative control with an invalid enum default was not caught; offline validation is not sufficient for semantic or database behavior checks.
- Xano server dry-run is **blocked** because `allow_push=false`; Claude stopped. No remote schema changes occurred.
- Architecture review recommendations (not deployed): keep case-sensitive segment name uniqueness for V1, normalize blank `external_id` to null in future APIs, keep `sensitive=true` fields but do not assume this enforces API access control, and enforce cross-product references in the API.
- Recommended path: save only these three XanoScript files in an isolated repository folder and commit; independently verify `auth/signup` External Access disabled and login unaffected; after approval temporarily enable direct CLI push; run **dry-run only**, require exactly 3 additions/0 updates/0 deletes; get a **separate approval** before the real push with interactive confirmation and no force/sync/delete/records/env/truncate.
- Avoid Xano's account-level sandbox reset or promotion if it may affect an unrelated Goodz sandbox. Direct push bypasses Xano's default sandbox review and therefore requires particularly strict scope.

## Market source commit verified (2026-10-22)
- Claude committed and pushed three **unchanged** XanoScript files at GitHub commit `f9c031591c3742c8534cac959330d55de8f3ca75`: `xano/market/table/products.xs`, `segments.xs`, and `customers.xs` (91 lines total).
- GitHub `main` was independently verified at `f9c0315` before this status update; source files were read and match the three reviewed schemas.
- Claude confirmed offline validation passed all three; **not yet server-validated or deployed to Xano**. `allow_push` is still reported off, and public signup lockdown remains unconfirmed.
- **Push working directory:** use `-d ./xano/market`, the directory containing `table/`, not `-d ./xano/market/table`. The latter omits Xano's expected relative `table/` folder.
- Next stage: user verifies signup External Access disabled plus owner login, then may explicitly and temporarily enable direct CLI push in Xano UI. Claude performs **server dry-run only** and shows an exact preview of three creates, zero changes/deletes. Actual push requires a separate approval.

## Server dry-run verification (Claude report, 2026-10-22)
- Git was at `472da99` with clean working tree; source hashes match committed `f9c0315` table definitions.
- Claude used `xano workspace push -p pmf -w 2 -b v1 -d ./xano/market --dry-run`. The server returned exit code 0 and previewed **exactly three creates**: `customers`, `products`, and `segments`; no existing-resource changes, deletes, records, APIs, or auth changes.
- Claude independently pulled workspace after the dry-run and reported no schema changes. The workspace still contains only the Xano auth starter and existing endpoints.
- Direct push setting `allow_push: true` was verified in workspace 2; **turn it back off immediately after the approved real push**.
- User confirmed to Claude that `auth/signup` External Access is disabled and owner login/`auth/me` work. An independent external signup-block test was **not performed** because an unexpectedly open endpoint could create a user.
- **Next gate:** real partial push, with an interactive confirmation; do not use `--force`, `--sync`, `--delete`, `--records`, `--env`, `--truncate`, or `--no-transaction`. Re-run dry-run immediately before it and stop if preview changes.
- After push: disable `allow_push`; inspect `pmf` schema and its indexes/references, unchanged `user`/auth endpoints and signup External Access state; note any local GUID/writeback modifications and reconcile them deliberately in Git. Never assume Git metadata changed remotely until independently verified.

## Phase 2 Batch 1 applied and verified (2026-10-22)
- Pre-push: Git clean at `f82ff6b` = `origin/main`; source hashes matched `f9c0315`; a repeat dry-run returned the identical preview (3 table CREATEs, nothing else).
- The real push could not be confirmed from Claude's non-TTY shell (CLI refuses without `--force`), so the **user ran the interactive partial push** `xano workspace push -p pmf -w 2 -b v1 -d ./xano/market` in their own terminal. No `--force`, `--sync`, `--delete`, `--records`, `--env`, `--truncate` or `--no-transaction`.
- Read-back (Claude, CLI pull of workspace 2 / `v1`): workspace now holds 9 documents — the 6 pre-existing (`workspace/pmf`, `table/user`, `Authentication` group, `auth/login`, `auth/me`, `auth/signup`) are **byte-identical** to the pre-push pull, plus `products`, `segments`, `customers`.
- The three server definitions match Git after normalizing formatting: fields, types, nullability/optionality, references (`owner_user_id`→`user`, `product_id`→`products`, `segment_id`→`segments`), filters, `sensitive` flags, enum values `prospect/active/former` with default `prospect`, and all indexes (incl. unique `segments(product_id,name)` and `customers(product_id,external_id)`). A comparator negative control (altered enum, index direction, nullability) was correctly detected. Server-side formatting differs only cosmetically: field `description` attributes are rendered as `//` comments, composite indexes are multi-line, the enum default is unquoted.
- CLI GUID writeback added one `guid = "…"` line to each of the three Git source files; GUIDs match the server's. These are committed so future pushes map to the same tables.
- `allow_push` verified **false** again via CLI after the user disabled it in the UI.
- **User-confirmed in the Xano UI (not independently testable by Claude):** `auth/signup` External Access still off; `products`, `segments`, `customers` each have 0 records. Claude's attempt to count records via the Metadata API was not completed (credential access was declined by the session's permission policy).

## Phase 2 Batch 2 prepared — Research schema review (2026-10-22)
- Claude prepared `interviews.xs`, `survey_waves.xs`, `survey_participations.xs` in its local scratchpad **only**. Reported 6/6 offline validation passes (including three Market controls), 7 malformed negative controls rejected by validator; five additional semantic errors passed validator but were caught by Claude's separate semantic checks.
- No Research tables exist in Xano and the proposed files are not committed yet. Workspace direct push remains disabled.
- Schema review accepted the **field definitions and indexes as written**, as a recommended V1 implementation baseline: interview history by customer/date, product survey waves by start time, one participation per wave/customer via composite uniqueness, indexed survey segmentation via snapshotted segment.
- Research design decisions (D-018–D-023): nullable survey start for drafts; nullable raw interview notes with minimum meaningful content enforced by future app/API before citation; raw observations untrimmed; closed waves read-only except explicit reopen, with no claimed audit log; permit partial responses without a PMF category but reject a category without responded_at; no unique survey name.
- Follow-up Phase 4 API requirements: wave must start before accepting responses; survey customer/product IDs must match; `segment_id_snapshot` is set on the server at eligibility and immutable; score denominator counts only responded_at plus valid `disappointment_level`; report partial respondents separately; historical product associations must not be altered after research exists.
- The server dry-run must test new-to-new table references and `enum values = ["very", "somewhat", "not"]`; offline validation does not prove semantics. Stop if the next server diff proposes **any change** to Market tables or existing auth.

## One next action
Have Claude copy only the three reviewed, unchanged Research XanoScript definitions from its scratchpad into `xano/research/table/`, revalidate, check for secrets and unrelated diffs, then commit/push **source files only**. No Xano settings, database changes, server dry-run, API development, or frontend work. After confirming the source commit, separately authorize temporary direct CLI push for server-side **dry-run only**.

## Approved-stack status
Xano selected; frontend still undecided between WeWeb and a coded frontend deployed on Vercel.

## Current risks
- `auth/signup` External Access is reported off by the user; the setting is not visible in XanoScript pulls, so re-confirm it in the UI after every push. Future APIs must also reject **all non-owner auth identities** (data-level owner IDs alone do not enforce a single-user application).
- Xano CLI `allow_push` is disabled (verified 2026-10-22 after Batch 1). Enabling it is explicitly flagged as critical by the CLI; requires separate approval and dry-run safeguards.
- Market tables enforce only native constraints (types, enums, unique indexes). Reference existence, same-product consistency (customer.segment.product = customer.product), blank-`external_id`→null normalization and owner checks must be implemented in the Phase 3 APIs.
- Always specify CLI profile `pmf` and workspace 2, never depend on the default profile; the Goodz instance is shared.
- The frontend has not been selected; Vercel is a deployment platform and requires a separate frontend implementation choice.
- Database-level cross-product referential integrity may require explicit API validation.
- Survey data alone does not prove retention, willingness to pay, or product-market fit.
- Real customer notes may contain personal information; use synthetic fixtures for development.

## Update policy
Only mark a phase complete when the corresponding real system change is evidenced by inspection/tests. Commit this file alongside durable implementation decisions; distinguish local draft, development, production, and frontend publication state.
