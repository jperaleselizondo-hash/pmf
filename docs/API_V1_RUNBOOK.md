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
xano workspace push -p pmf -w 2 -b v1 -d ./xano/app --dry-run | tee /tmp/pmf-dry-run.txt
python3 -I tests/static/check_dry_run.py /tmp/pmf-dry-run.txt
```
Accept only: CREATE-only; 1 API group + 48 endpoints + 34 functions (83); zero table, auth or other changes. Any difference → stop, disable push.

## 3. Real push (separate approval; owner runs it interactively)
```
xano workspace push -p pmf -w 2 -b v1 -d ./xano/app      # answer y only if the preview is identical
```
Then the owner disables direct push and it is verified:
```
xano workspace get -p pmf -w 2 -o json                   # allow_push MUST be false (D-025)
xano workspace pull -p pmf -w 2 -b v1 -d /tmp/pmf-after
python3 -I tests/static/compare_readback.py /tmp/pmf-after --baseline /tmp/pmf-before
```
Keep the CLI-written `guid` lines in `xano/app` and commit them.

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
Also run once: `xano unit_test run_all -p pmf -w 2 -b v1` (pure-function unit tests; they do not write data).
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
Cleanup reads all rows of the ten business tables, STOPS without deleting if any row is not provably synthetic (SYNTH- product of the owner, every child chained to it, synthetic customer names/emails), deletes the verified ids children-first, removes only the synthetic test user identified by its own `auth/me` (never the owner, never truncate), then verifies all ten tables have zero rows (exit 4 otherwise).

## 6. Recovery after a partially failed run
- Fixture or matrix failure, aborted run, or gate abort after sweeps: synthetic data may remain. Do not hand-delete. Run the cleanup dry run; if it reports STOP, inspect the listed rows in the UI before anything else.
- `require_empty` failure before testing: real or leftover data exists — do not run tests or cleanup until the owner explains it.
- Cleanup exit 4 (rows remain): rerun the dry run; never truncate; investigate rows that are not in the plan.
- Lost ledger: cleanup does not depend on it (it verifies every row); the ledger only reports which rows a run created.
- Rollback of the deployment: set `active = false` in `xano/app/api/pmf_app/api_group.xs` and push it through the same dry-run/approval gate, or remove the group and functions in the UI. No table or auth change is involved.
