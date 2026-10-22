# PMF Engine API V1 — tests

Specification: `docs/API_V1_PROPOSAL.md` (branch `docs/api-v1-design`, Appendix R8).

## Offline (safe anywhere; no network, no Xano)
| Check | Command |
|---|---|
| XanoScript syntax (all sources) | `XANO_DEV_MCP_LIB=<path>/@xano/developer-mcp/dist/lib.js node tests/static/validate_xs.mjs xano/app xano/market xano/research xano/intelligence_validation` |
| Project rules (inventory, owner guard, loaders, routes, fields, sensitive inputs, mass-assignment, error codes, pagination, forbidden constructs) | `python3 -I tests/static/xs_api_lint.py .` |
| Safety guard + PMF reference values | `python3 -m unittest discover -s tests/api -p 'test_offline.py'` |

XanoScript unit tests are defined inline (`test "…"` blocks) in the pure functions under `xano/app/function/pmf/{text,util,survey,report,insight,validation}`. They run on the server (`xano unit_test run_all`) — **only in the isolated environment**.

## HTTP suite (isolated environment ONLY)
`tests/api/pmf_api_tests.py` writes synthetic records. It must never target live `v1`.

Mandatory safety protocol (Appendix R8.5), enforced by `tests/api/safety.py` before the first write:
1. Base/auth URLs use https; host ≠ live host (`xgjc-aodb-3a7q.n7e.xano.io`, hard-denied).
2. Host equals `PMF_TEST_ENV_HOST` (operator-recorded isolated tenant host); base path starts with `/api:pmf-app`.
3. `--confirm-tenant` equals `PMF_TEST_TENANT_NAME`.
4. Read-only canary: owner and intruder `auth/me` emails end with `@pmf-test.invalid` and differ; every existing product name starts with `SYNTH-`.
5. Tokens come from environment variables only; nothing is written to disk.

Operator setup inside the isolated environment (after approval): push tables + `xano/app`; create two users with `@pmf-test.invalid` emails; set that environment's `PMF_OWNER_USER_ID` to the synthetic owner's id; obtain both tokens via that environment's `auth/login`.

```
export PMF_TEST_BASE_URL=https://<isolated-host>/api:pmf-app
export PMF_TEST_AUTH_URL=https://<isolated-host>/api:<auth-canonical>
export PMF_TEST_ENV_HOST=<isolated-host>
export PMF_TEST_TENANT_NAME=<tenant-name>
export PMF_TEST_OWNER_TOKEN=...      # never commit
export PMF_TEST_INTRUDER_TOKEN=...   # never commit
python3 tests/api/pmf_api_tests.py --confirm-tenant <tenant-name>
```

Coverage: security S01–S07 (S03/S08/S09 manual), market M01–M07, research R01–R05, surveys W01–W11, numeric/cohort P01–P09, evidence E00–E09, insights I01–I05, validation V01–V05, concurrency C01–C04 (U13 gate), end-to-end X01. Fixture = docs/08 wave (5 eligible, 4 invited, 3 valid, PMF 33.333…%).
