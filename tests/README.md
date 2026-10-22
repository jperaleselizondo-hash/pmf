# PMF Engine API V1 — tests

Specification: `docs/API_V1_PROPOSAL.md` (branch `docs/api-v1-design`, Appendix R8).

## Offline (safe anywhere; no network, no Xano)
| Check | Command |
|---|---|
| XanoScript syntax (all sources) | `XANO_DEV_MCP_LIB=<path>/@xano/developer-mcp/dist/lib.js node tests/static/validate_xs.mjs xano/app xano/market xano/research xano/intelligence_validation` |
| Project rules (inventory, owner guard, loaders, routes, fields, sensitive inputs, mass-assignment, error codes, pagination, forbidden constructs, ambiguous filter chains) | `python3 -I tests/static/xs_api_lint.py .` |
| Harness: preflight, guarded client, S01/S02 gate, concurrency gate, inventory consistency, PMF reference values | `python3 -m unittest discover -s tests/api -p 'test_offline.py'` |

XanoScript unit tests are inline `test "…"` blocks in the pure functions under `xano/app/function/pmf/{text,util,survey,report,insight,validation}`; they run server-side (`xano unit_test run_all`) — **only in the isolated tenant**.

## HTTP suite (isolated ephemeral tenant ONLY)
`tests/api/pmf_api_tests.py` writes synthetic records and must never target live `v1`.

### Preflight (exit 2, before any request with a write verb)
1. **Configuration** (`safety.check_config`): https only; no credentials/port/query; live host `xgjc-aodb-3a7q.n7e.xano.io` hard-denied; base and auth URLs on the same host and branch; base path exactly `/api:pmf-app` or `/api:pmf-app:<branch>` (the Xano form `<host>/api:<canonical>[:<branch>]`; tenant-specific path prefixes are undocumented and therefore rejected); `--confirm-tenant` equals `PMF_TEST_TENANT_NAME`.
2. **Authoritative identity** (`safety.fetch_tenant_metadata` + `check_tenant_metadata`): runs the read-only `xano ephemeral get <name> -p pmf -w 2 -o json`; the record's `name` must match, `ephemeral_expires_at` must exist and be ≥ 10 minutes away, `state` must not indicate deletion/failure, and the configured host must be the tenant's `xano_domain` (or its custom `domain`). A tenant whose domain is the live host is refused — isolation cannot then be proven by host.
3. **Read-only canary** (`safety.check_canary`): owner and intruder `auth/me` on that host return different ids with `@pmf-test.invalid` emails; the complete product list (≤ 100) contains only `SYNTH-` names.
4. **Guarded client** (`http_client.Api`): only the 48 inventory routes plus `GET auth/me`, only the verified host, redirects never followed.

### Gate (exit 3)
S01 (no-token sweep → 401) and S02 (non-owner sweep → 403) always run — `--only` cannot skip them — and must both pass before the fixture or any business data is created. Offline tests prove that a failure of either leaves only canary and sweep requests in the log.

### Concurrency gate (U13) — any failure blocks deployment
The parent-row no-op updates in `pmf/lock/{wave,insight}` are **not assumed to lock**. C01–C04 run `--trials` (default 25, minimum 10) fresh trials each; workers are released together by a barrier; each trial asserts a final-state invariant:
| Test | Race | Invariant per trial |
|---|---|---|
| C01 | 4 × add the same customer to a fresh wave | exactly 1 row and 1 success |
| C02 | delete both evidence rows of a reviewed insight | reviewed insight keeps ≥ 1 evidence; not both deletes succeed |
| C03 | close wave vs record a response | close succeeds; edit is 200 or `WAVE_CLOSED`; a written response has `updated_at ≤ closed_at`; a rejected edit is not persisted |
| C04 | create hypothesis vs unreview | never a hypothesis on a draft insight; not both succeed |
A result fails on any violation, on request errors, or as **inconclusive** when fewer than 80 % of trials had all requests in flight simultaneously (client side). Client-side overlap is necessary, not sufficient, evidence of server interleaving. **Required negative control before deployment:** in the isolated tenant only, push a variant with the lock calls removed and run C02–C04 again; they must fail at least once. If they never fail, the suite cannot detect the race and the locking strategy remains unproven.

### Operator setup (after approval, isolated tenant only)
Push tables + `xano/app` to the ephemeral tenant; create two users with `@pmf-test.invalid` emails; set that tenant's `PMF_OWNER_USER_ID` to the synthetic owner's id; obtain tokens from that tenant's `auth/login`.
```
export PMF_TEST_BASE_URL=https://<tenant xano_domain>/api:pmf-app
export PMF_TEST_AUTH_URL=https://<tenant xano_domain>/api:<auth-canonical>
export PMF_TEST_TENANT_NAME=<tenant-name>
export PMF_TEST_OWNER_TOKEN=...      # never commit
export PMF_TEST_INTRUDER_TOKEN=...   # never commit
python3 tests/api/pmf_api_tests.py --confirm-tenant <tenant-name> --trials 25
```

## Coverage
Automated: S01, S02, S04–S07 · M01–M07 · R01–R05 · W01–W11 · P01–P09 · E00–E09 · I01–I05 · V01–V05 · C01–C04 · X01–X02 (64). Manual: S03 (owner env unset → 500), S08 (request-history masking), S09 (live signup External Access). All 48 routes are exercised on the owner path (X02 covers the read/list/update routes not otherwise used).

docs/05 definitions of done: 1 API side only (S01/S02/canary; login/logout UI is frontend) · 2 fixture · 3 fixture W1 · 4 P01–P03 · 5 E08 · 6 V01, V04 · 7 X01 · 8 M03, W02, W03, E01–E06.

### Tests that depend on unverified runtime behavior
| Assumption | Tests |
|---|---|
| Auth is checked before input validation (401 for every route) | S01 |
| Sample bodies pass input validation so `require_owner` runs (403) | S02 |
| Unknown inputs are ignored or rejected (either accepted) | S05, M07 |
| Error envelope carries `message` starting with our `CODE:`; status per error type (400/403/404/500) | most negative tests |
| Timestamp inputs accept epoch ms; `now`/`transform_timestamp` comparisons | R04, W06, W08, P01, C03 |
| Optional text without `filters=trim` is stored verbatim; whitespace passes required-text validation | R01, X01, E07 |
| Precondition failure inside `db.transaction` rolls back earlier writes | W03 |
| GET booleans/ints from query strings (`unsegmented=true`, `per_page`) | P02, X02 |
| `per_page` above the `max:100` filter is rejected with 400 | X02 |
| `includes` search semantics (case) | X02 |
| `return` from nested conditionals; outer variables inside `filter:` expressions | P01–P09 |
| Row locking / transaction isolation | C01–C04 (gate) |
