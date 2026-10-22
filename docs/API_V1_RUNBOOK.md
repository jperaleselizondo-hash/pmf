# API V1 — deployment, live synthetic testing and cleanup runbook

Owner decision (Phase 3): the API is deployed to and tested in the existing Xano workspace `pmf` (ID 2), branch `v1`, instance `xgjc-aodb-3a7q`, using synthetic records that are purged afterwards. No other workspace, tenant, sandbox or data source is created. Goodz is never targeted: every command pins `-p pmf -w 2`.

Every numbered step that changes Xano needs its own explicit approval. Never use `--force`, `--sync`, `--delete`, `--records`, `--env`, `--truncate` or `--no-transaction`.

## 0. Preconditions (read-only)
```
git switch main && git pull --ff-only          # deploy only reviewed, merged source
xano profile get                               # note the default; all commands below pass -p pmf explicitly
xano workspace get -p pmf -w 2 -o json         # id 2, name pmf, allow_push false
xano branch list -p pmf -w 2                   # v1 (live) only
xano workspace pull -p pmf -w 2 -b v1 -d /tmp/pmf-before    # baseline: 16 documents, no PMF App objects
```
Owner confirms in the Xano UI: `auth/signup` External Access OFF; the ten business tables have 0 records.

## 1. Owner configuration (UI, owner only)
- Read your user id from `GET auth/me` (your own login) and set workspace environment variable `PMF_OWNER_USER_ID` to it. Never commit it.
- Create one synthetic non-owner user (Database → `user`), email `<anything>@pmf-test.invalid`, strong random password. Note its id.
- Create a Metadata API access token limited to what the tests need: Workspace Content Read (tests) and Workspace Content Delete (cleanup). Keep it outside Git.

## 2. Dry-run (temporary direct push)
Owner enables Workspace Settings → CLI → Allow Direct Workspace Push for `pmf` only, then:
```
xano workspace get -p pmf -w 2 -o json                 # confirm allow_push true
set -o pipefail                                        # keep the CLI's exit status through tee (bash and zsh)
xano workspace push -p pmf -w 2 -b v1 -d ./xano/app --dry-run 2>&1 | tee /tmp/pmf-dry-run.txt
DRY_RUN_EXIT=$?
python3 -I tests/static/check_dry_run.py /tmp/pmf-dry-run.txt --cli-exit "$DRY_RUN_EXIT"
```
(Without a pipe: `xano … --dry-run > /tmp/pmf-dry-run.txt 2>&1; DRY_RUN_EXIT=$?`.)
The checker requires the preview header for workspace 2, the identity line `xgjc-aodb-3a7q.n7e.xano.io | pmf`, a complete changes section, CREATE-only lines of known types, no table/auth objects, and the exact inventory: `PMF App` (pmf-app), the 34 local function names and the 48 local (verb, route) endpoints.
- exit 0: exact inventory verified → may proceed to the separately approved push.
- exit 3: structure and counts match but the preview does not show HTTP verbs, so individual endpoints cannot be uniquely identified → **explicit human review** of `/tmp/pmf-dry-run.txt` against `docs/API_V1_PROPOSAL.md` R8.3 is required; do not treat as verified.
- exit 1: anything else (including unknown type labels, which require a deliberate checker update after review) → stop, disable push.

## 3. Real push (separate approval; owner runs it interactively)
```
xano workspace push -p pmf -w 2 -b v1 -d ./xano/app      # answer y only if the preview is identical
```
Then the owner disables direct push and it is verified:
```
xano workspace get -p pmf -w 2 -o json                   # allow_push MUST be false (D-025)
xano workspace pull -p pmf -w 2 -b v1 -d /tmp/pmf-after
python3 -I tests/static/compare_readback.py /tmp/pmf-after --baseline /tmp/pmf-before --json /tmp/pmf-readback.json
```
The comparator classifies every deployed object as EQUIVALENT (documented re-formatting only), RUNTIME (plausible server normalization that must be proven by a named runtime test) or UNEXPLAINED. Exit 0 means structural verification passed (no missing/extra/unexplained objects, GUIDs match, 16 pre-existing documents unchanged); RUNTIME gates are printed and must pass in §4 before acceptance. Exit 1 → stop.
Keep the CLI-written `guid` lines in `xano/app` and commit them (GUID lines only). Never copy Xano's re-printed definitions into the repository.

## 4. Runtime tests (synthetic data, live workspace)
```
export PMF_TEST_BASE_URL=https://xgjc-aodb-3a7q.n7e.xano.io/api:pmf-app
export PMF_TEST_AUTH_URL=https://xgjc-aodb-3a7q.n7e.xano.io/api:xHMmrw_d
export PMF_TEST_OWNER_ID=<verified owner id>
export PMF_TEST_OWNER_TOKEN=<owner token from auth/login>        # never commit
export PMF_TEST_INTRUDER_TOKEN=<synthetic user token>            # never commit
export PMF_XANO_META_TOKEN=<metadata token>                      # never commit
python3 tests/api/pmf_api_tests.py --target live-pmf \
  --confirm-live synthetic-tests:xgjc-aodb-3a7q:workspace-2:pmf-app --trials 25
```
Sequence enforced by the runner: fixed-target config → CLI identity (instance, workspace 2 = pmf) → read-only pull confirms canonicals `pmf-app` and `xHMmrw_d` → all ten business tables empty → canary (owner id matches `PMF_TEST_OWNER_ID`, intruder synthetic, no products) → **S01/S02 gate** → tables still empty → fixture → matrix → C01–C04 repeated trials (25 each) → X01/X02 → S06. A ledger of created ids is written to `~/.pmf-test-runs/`.
Also run once: `xano unit_test run_all -p pmf -w 2 -b v1` (pure-function unit tests; they do not write data). This is the runtime gate for the `count_wave` test inputs that Xano stored as expression blocks.
Deployment runtime gates (Phase 3 read-back, D-036) are asserted by P02/P03/P09/X02 (`unsegmented` defaults and filters, participation pagination), V02–V04 (experiment validation on create; no rejected experiment persisted; fields persist) and E05/E06/E08 (survey `source_field` validation).
Manual checks: S03 (temporarily unset `PMF_OWNER_USER_ID` → 500 on any business endpoint, then restore), S08 (request history masking), S09 (signup External Access).

### Concurrency residual risk
The lock-free negative control is **not** run in the live workspace. A passing C01–C04 means no invariant violation was observed in the recorded trials with concurrent overlap; it does not prove the tests could detect a race or that the no-op parent update locks. Any violation or inconclusive result blocks acceptance. If guarantees cannot be established, the residual risk (single owner, rare double-submit) must be accepted explicitly by the owner or the lock strategy changed (e.g. parent `updated_at` write) and re-tested.

## 5. Cleanup (separate approval)
```
python3 tests/api/cleanup_live.py --confirm-cleanup delete-synthetic:xgjc-aodb-3a7q:workspace-2 \
  --ledger ~/.pmf-test-runs/run-<tag>.jsonl                            # dry run: verification + plan only
python3 tests/api/cleanup_live.py --confirm-cleanup delete-synthetic:xgjc-aodb-3a7q:workspace-2 \
  --ledger ~/.pmf-test-runs/run-<tag>.jsonl --execute --remove-test-user
```
Cleanup reads all rows of the ten business tables (the Metadata API reply must be well-formed: integer `itemsTotal` ≥ 0, list `items` with integer ids, complete and consistent pagination, fetched rows = `itemsTotal`; otherwise STOP), STOPS without deleting if any row is not provably synthetic (SYNTH- product of the owner, every child chained to it, synthetic customer names/emails), re-counts all ten tables immediately before deleting (any change since verification → STOP), deletes the verified ids children-first — each DELETE must return 200 (documented) or 204 (tolerated) **and** a follow-up read of that record must return 404, otherwise it stops with exit 4 — removes only the synthetic test user identified by its own `auth/me` (never the owner, never truncate), then verifies all ten tables have zero rows (exit 4 otherwise).

## 6. Recovery after a partially failed run
- Fixture or matrix failure, aborted run, or gate abort after sweeps: synthetic data may remain. Do not hand-delete. Run the cleanup dry run; if it reports STOP, inspect the listed rows in the UI before anything else.
- `require_empty` failure before testing: real or leftover data exists — do not run tests or cleanup until the owner explains it.
- Cleanup exit 4 (a delete was not confirmed, or rows remain): deletion stopped at that row; rerun the dry run (it re-verifies everything); never truncate; investigate rows that are not in the plan.
- Any STOP caused by a malformed or contradictory Metadata API reply: nothing was deleted; do not retry blindly — capture the status and report it.
- Lost ledger: cleanup does not depend on it (it verifies every row); the ledger only reports which rows a run created.
- Rollback of the deployment: set `active = false` in `xano/app/api/pmf_app/api_group.xs` and push it through the same dry-run/approval gate, or remove the group and functions in the UI. No table or auth change is involved.
