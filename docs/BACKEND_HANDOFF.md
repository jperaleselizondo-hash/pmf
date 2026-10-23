# PMF Engine — Backend handoff (Phase 3, 2026-10-23)

Read this before resuming PMF Engine work. The project is **paused** after backend QA so the owner can return to the Goodz launch. No frontend exists; the WeWeb vs coded-frontend-on-Vercel decision is still open.

## What is live
- Xano instance `xgjc-aodb-3a7q` (shared with Goodz — never target workspace 1), workspace `pmf` ID 2, branch `v1` (live, only branch). Always pass `-p pmf -w 2`.
- 10 business tables (`products`, `segments`, `customers`, `interviews`, `survey_waves`, `survey_participations`, `insights`, `insight_evidence`, `hypotheses`, `experiments`) plus the Xano `user` auth table. All ten business tables are **empty**; `user` holds only the owner (id 1).
- API group `PMF App` (canonical `pmf-app`): 48 endpoints, 34 functions. Authentication group `xHMmrw_d` unchanged. Every business endpoint requires auth and the owner guard (`PMF_OWNER_USER_ID` = 1, workspace environment variable).
- Source of truth: `xano/app` (API), `xano/market`, `xano/research`, `xano/intelligence_validation` (tables) at `main`. Server GUIDs are committed; never adopt the server's re-printed XanoScript as source (it drops grouping parentheses, bool defaults, and stores some object literals in expression mode).

## Verification evidence (final run)
- Server unit tests: **66 passed, 0 failed** (`xano unit_test run_all -p pmf -w 2 -b v1`).
- HTTP suite (`tests/api/pmf_api_tests.py --target live-pmf --trials 25`): **64/64 automated tests passed**, including C01–C04 (25 barrier-synchronized trials each, strict serialized-outcome checks, ≥80% overlap gate) and T01 (transaction rollback + positive control).
- Read-back comparator after the last deployment: EQUIVALENT 78 · RUNTIME 5 · UNEXPLAINED 0 (the 5 RUNTIME items are known server re-formattings, each covered by a passing runtime test).
- Cleanup: all synthetic rows deleted by `tests/api/cleanup_live.py`, ten tables verified at zero, temporary test user id 2 removed (its token now gets 403 `NOT_OWNER`).

## Security checks
| Check | Status |
|---|---|
| S01/S02 (401/403 sweeps), S04–S07 | Passed (automated). |
| S03 owner variable unset → 500 | **Code review passed; live runtime check NOT EXECUTED** (owner decision: do not unset `PMF_OWNER_USER_ID` live). `pmf/auth/require_owner` fails closed on a missing/blank value. |
| S08 request-history masking | **Partial.** Read-only scan of 5,071 history entries: sensitive inputs (customer name/email, interview notes) masked; no test tokens or Authorization headers stored. Response **outputs** are retained and contain sensitive fields → owner should reduce/disable output history for `PMF App` in the Xano UI. |
| S09 `auth/signup` External Access blocked | **Manual UI check pending** (never automated: an unblocked call could create a user). |

## Known residual risks
- Concurrency rests on `pmf/lock/*` writing `updated_at = now` inside `db.transaction` (real row lock). Live evidence: the same harness detected 20/25 and 21/25 violations under the old no-op lock and 0 under the new one; no deliberate live negative control was run. Side effect: parent `updated_at` also moves on child writes.
- Not covered: a three-way race involving deletion of an evidence source (interview/participation) while evidence is being created; judged low risk for a single-user V1.
- Wave-close root cause (`$input.closed_at ?? now`) was fixed by avoiding the construct; the exact server semantics remain unconfirmed.
- Blank text on PATCH means "unchanged"; fields are cleared only with an explicit `clear` allow-list (D-039).
- `allow_push` has repeatedly stayed on after pushes; always verify `xano workspace get -p pmf -w 2 -o json` shows `allow_push: false`.

## Owner actions outstanding
1. Revoke the two temporary Metadata API tokens (Workspace Content Read, and Read + Delete for cleanup), then delete the local file `~/.config/pmf/test.env` (it also holds expired/obsolete session tokens). Neither token is in Git.
2. S08: reduce/disable response-output request history for `PMF App`.
3. S09: confirm `auth/signup` External Access is OFF.

## Resuming later
- Runbook: [API_V1_RUNBOOK.md](API_V1_RUNBOOK.md) (dry-run gate → owner interactive push → read-back → unit tests → HTTP suite → cleanup). A re-run needs a new synthetic test user and new temporary Metadata tokens.
- Status and history: [PROJECT_STATUS.md](PROJECT_STATUS.md), [DECISION_LOG.md](DECISION_LOG.md); contract: [API_V1_PROPOSAL.md](API_V1_PROPOSAL.md).
- Next product step after the Goodz launch: the frontend decision (WeWeb vs coded frontend on Vercel). Do not start it before then.
