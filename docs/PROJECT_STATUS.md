# Project Status

**Date:** 2026-10-23
**Milestone:** Phase 3 API V1 **deployed and structurally verified** in Xano; **runtime validation pending** (no HTTP/unit tests executed yet)
**Product build:** Xano workspace `pmf` (ID 2), branch `v1` (live): auth starter, ten empty business tables, `PMF App` API group (`pmf-app`) with 48 endpoints and 34 functions; endpoints refuse all calls until `PMF_OWNER_USER_ID` is set (fail-closed); no records in business tables (owner-confirmed before push), no frontend
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
- [x] Phase 2: Physical Xano schema — Batch 1 (Market), Batch 2 (Research) and Batch 3 (Intelligence + Validation: `insights`, `insight_evidence`, `hypotheses`, `experiments`) applied and verified; schema only, no records or APIs
- [ ] Phase 3: Consolidated API V1 (all business domains) — deployed and structurally verified 2026-10-23; runtime validation pending
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

## Phase 2 Batch 2 Research source-control milestone (Claude report, 2026-10-22)
- GitHub `main` independently verified at `fb3e6ba2155a93054b96c1bd0dc6ff672d167ce8`; files present at `xano/research/table/interviews.xs`, `survey_waves.xs`, and `survey_participations.xs` (123 lines total).
- Claude reported all three exactly match its reviewed scratchpad definitions, passed the offline XanoScript validator v2.2.6 and additional semantic checks; three Market definitions unchanged. No credentials, production records or generated sync state included.
- **No Xano changes** occurred in this source-only step. Research tables are not live; `allow_push` remains reported false. Per-table GUIDs will be assigned only after a future successful server push.
- The Research design remains D-018 through D-023. The decision-log Markdown table formatting was corrected in this same documentation-only update.

## Phase 2 Batch 2 applied and verified (2026-10-22)
- Server dry-run (Claude, `xano workspace push -p pmf -w 2 -b v1 -d ./xano/research --dry-run`, Git at `981e7c2`): exactly three CREATEs — `interviews`, `survey_participations`, `survey_waves`; no updates, deletes, records, Market/auth changes or validation errors. New-to-new references and `disappointment_level` values `very`/`somewhat`/`not` accepted. Workspace pull before and after the dry-run was identical.
- Real interactive partial push was run by the user outside Claude's session (no `--force`/`--sync`/`--delete`/`--records`/`--env`/`--truncate`/`--no-transaction`).
- Read-back (Claude, CLI pull of workspace 2 / `v1`): 12 documents. The 9 pre-existing definitions (`workspace/pmf`, `user`, `products`, `segments`, `customers`, `Authentication` group, `auth/login`, `auth/me`, `auth/signup`) are **byte-identical** to the pre-push pull. The three Research tables match `xano/research/table/*.xs` after formatting normalization (fields, types, nullability, references, filters, `sensitive` flags, enum values, indexes).
- CLI writeback added one `guid = "…"` line per Research file; all three match the server and are committed with this update.
- `allow_push`: after the push the CLI still reported **true** even though the UI had been reported disabled; the user re-toggled it and Claude verified **false** via CLI before this commit. Lesson: always confirm the push setting via CLI, not only the UI.
- **User-confirmed in the Xano UI (not independently testable by Claude):** `auth/signup` External Access still off; `interviews`, `survey_waves`, `survey_participations` each have 0 records.

## Final schema source merge (2026-10-22)
- Claude inspected four revised XanoScript definitions at feature commit `2f16cf5`; reported 10/10 offline syntax and semantic checks passed across all business tables, and 9/9 revision-focused negative controls were detected. All references resolve, no duplicate table names, no blocking architecture decisions.
- GitHub final feature review instructions were updated (commit `29cd556`) after Research Batch 2 closure at `c32af8b`.
- GitHub PR #1 merged the feature branch into `main` in commit `d0812308259945ccd9733b3f3b5481a93c14d53a`. Scope is exactly five **new** files in `xano/intelligence_validation/`: four XanoScript table definitions and `REVIEW.md`.
- **Source-only merge:** no Xano mutation, server-side dry-run or actual schema push performed. All 10 business-table definitions are now in Git; 6 of 10 business tables are live in Xano.
- The next task is the server-side dry-run for exactly four CREATEs. Ensure `allow_push=false` at rest, verify owner login/signup lock, temporarily enable direct push in `pmf` workspace 2 only for the preview, then separately approve the real interactive push.
- Once all ten tables are live and verified, the user prefers **one consolidated API implementation batch** covering owner authorization, Market/Research CRUD, surveys/PMF reporting, evidence/insights, hypotheses and experiments. Maintain internal validation checkpoints and separate explicit production-write approval.

## Phase 2 Batch 3 applied and verified — final schema (2026-10-22)
- Server dry-run (Claude, `xano workspace push -p pmf -w 2 -b v1 -d ./xano/intelligence_validation --dry-run`, Git at `2ecad90`, merged files byte-identical to validated `2f16cf5`): exactly four CREATEs — `experiments`, `hypotheses`, `insight_evidence`, `insights`; no updates, deletes, records or existing-resource changes. Server accepted enum field names `type`/`relationship`, enum defaults, nullable enums, all references and the three-column `insights(product_id, review_status, created_at desc)` index. Workspace pull before and after the dry-run was identical.
- Real interactive partial push was run by the user outside Claude's session (no `--force`/`--sync`/`--delete`/`--records`/`--env`/`--truncate`/`--no-transaction`).
- Read-back (Claude, CLI pull of workspace 2 / `v1`): 16 documents. The 12 pre-existing definitions (workspace, `user`, 3 Market, 3 Research tables, `Authentication` group and its 3 endpoints) are **byte-identical** to the pre-push pull. The four new tables match `xano/intelligence_validation/table/*.xs` after formatting normalization.
- CLI writeback added one `guid = "…"` line per file; all four match the server and are committed with this update.
- `allow_push` verified **false** via CLI after the user disabled it.
- **User-confirmed in the Xano UI (not independently testable by Claude):** `auth/signup` External Access still off; `insights`, `insight_evidence`, `hypotheses`, `experiments` each have 0 records.

## Phase 3 source merge verified (2026-10-23)
- **GitHub only:** PR #2 merged `docs/api-v1-design` to `main` at `0a1fe60`. `docs/API_V1_PROPOSAL.md` preserves the 48-endpoint contract, U1–U14 decisions, and the existing-workspace synthetic test strategy in Appendix R9.
- **GitHub only:** PR #3 merged `feat/api-v1` at `597918640dbeb6f693b12af646110195fc8face2`. Adds 1 API group definition, 48 query definitions, 34 reusable function definitions, static checks, guarded live-workspace synthetic test suite and cleanup/runbook. All files are source files, **not deployed**.
- Claude reports 93/93 XanoScript files offline-valid, 91/91 offline unit tests passing, 28/28 dry-run-checker negative controls, 18/18 static-checker negative controls. These are offline observations, **not runtime success**.
- User chose existing `pmf` workspace 2, live `v1`, for synthetic testing followed by a verified selective purge. No new workspace/tenant. Safeguards require ten business tables empty before tests, fixed workspace identity, explicit confirmations, owner/non-owner checks, and delete-by-verified-ID cleanup.
- Current Xano state last reported by Claude: 16 schema definitions, 10 empty business tables, only existing Authentication APIs, **no deployed PMF business APIs**, and `allow_push: false`. None of the GitHub merges touched Xano.
- Important unproven runtime dependencies: exact CLI dry-run output and API canonical uniqueness; Metadata API pagination/content permissions; HTTP semantics and transaction rollback; survey calculations; no-op parent-lock effectiveness. All runtime testing and any production changes still require their own approval.

## Phase 3 API V1 deployed — structural verification (2026-10-23)
- Server dry-run (Claude, Git `11a4696`, CLI exit 0) listed exactly 83 CREATEs; `tests/static/check_dry_run.py` PASS (exact inventory: `PMF App`, 34 functions, 48 verb+route endpoints, cross-checked against Proposal R8.3). Workspace unchanged by the dry-run.
- Owner ran the approved interactive push (push output not supplied to Claude). Direct push was still on afterwards; owner disabled it and Claude verified `allow_push: false` via CLI.
- Read-back `/tmp/pmf-after`: 99 documents = 16 pre-existing (byte-identical to the pre-deployment baseline) + 83 new; `PMF App` canonical `pmf-app`; Authentication canonical unchanged (`xHMmrw_d`); 48 PMF endpoints, 34 functions; all 83 server GUIDs match the CLI writeback, which is committed (GUID lines only — source logic unchanged).
- `tests/static/compare_readback.py` (repaired): **EQUIVALENT 77 · RUNTIME 6 · UNEXPLAINED 0**. Documented equivalences: comments/descriptions/GUIDs, quoted vs unquoted names (the earlier "missing `GET/POST products`" was a comparator bug), whitespace/commas, default `type: inner`, default `error_type = "standard"`, `expect.to_throw {exception = ""}`, api_group attribute order, parentheses around complete values/atomic filter arguments.
- **Runtime gates (not proven equivalent; must pass before acceptance):**

  | Deployed object | Server normalization | Gate |
  |---|---|---|
  | `pmf/report/build_wave_report`, `GET survey-waves/{wave_id}/report`, `GET survey-waves/{wave_id}/participations` | `bool …?=false` defaults dropped (`unsegmented`, `summary`) | P02/P03 (omitted `unsegmented` → `false`, explicit true/false), P09, X02 |
  | `POST hypotheses/{hypothesis_id}/experiments` | validation state stored in backtick expression mode | V02, V03 (no rejected experiment persisted), V04 (fields persist) |
  | `pmf/evidence/validate_source` | parentheses dropped inside the survey `source_field` precondition | E05, E06, E08 |
  | `GET survey-waves/{wave_id}/participations` | parentheses dropped in `slice:$offset:($offset + $input.per_page)` | X02 pagination |
  | `pmf/report/count_wave` | inline test inputs stored as expression blocks | server-side unit tests (`xano unit_test run_all -p pmf -w 2 -b v1`) |
- The repository source stays authoritative; Xano's re-printed text must never be adopted as source (some printed forms omit parentheses required by greedy filter binding).
- Not verified by Claude: "no new business records" after the push (needs owner UI check or the scoped Metadata token); Goodz not inspected (all commands pinned to `-w 2`).

## One next action
Runtime validation preparation (owner actions, each separately approved): set `PMF_OWNER_USER_ID` from the verified `auth/me` id; create one `@pmf-test.invalid` non-owner user; create a Metadata API token scoped to Workspace Content Read/Delete; confirm the ten business tables are still empty. Then run the HTTP suite with `--target live-pmf` (runbook §4), the server-side unit tests, and the manual checks; every runtime gate above and C01–C04 must pass (or the concurrency residual risk be explicitly accepted). Cleanup follows as a separate approval.

## Approved-stack status
Xano selected; frontend still undecided between WeWeb and a coded frontend deployed on Vercel.

## Current risks
- `auth/signup` External Access is reported off by the user; the setting is not visible in XanoScript pulls, so re-confirm it in the UI after every push. Future APIs must also reject **all non-owner auth identities** (data-level owner IDs alone do not enforce a single-user application).
- Xano CLI `allow_push` is disabled (verified via CLI 2026-10-22 after Batch 3). The UI toggle once appeared off while the CLI still reported true; always verify via `xano workspace get -p pmf -w 2`. Enabling it is explicitly flagged as critical by the CLI; requires separate approval and dry-run safeguards.
- Research tables enforce only native constraints (types, enums, unique `(survey_wave_id, customer_id)`). Same-product survey membership, server-assigned immutable segment snapshots, valid-response rules, wave locking and closed-wave protection are Phase 4 API work (D-018–D-023).
- Intelligence/Validation tables enforce only native constraints (types, enums, defaults). Evidence source XOR, same-product evidence/segment checks, reviewed-insight evidence requirement, hypotheses only on reviewed insights, `source_field` validation and experiment consistency are API work (D-027–D-029, `REVIEW.md`).
- Market tables enforce only native constraints (types, enums, unique indexes). Reference existence, same-product consistency (customer.segment.product = customer.product), blank-`external_id`→null normalization and owner checks must be implemented in the Phase 3 APIs.
- Always specify CLI profile `pmf` and workspace 2, never depend on the default profile; the Goodz instance is shared.
- The frontend has not been selected; Vercel is a deployment platform and requires a separate frontend implementation choice.
- Database-level cross-product referential integrity may require explicit API validation.
- Survey data alone does not prove retention, willingness to pay, or product-market fit.
- Real customer notes may contain personal information; use synthetic fixtures for development.

## Update policy
Only mark a phase complete when the corresponding real system change is evidenced by inspection/tests. Commit this file alongside durable implementation decisions; distinguish local draft, development, production, and frontend publication state.
