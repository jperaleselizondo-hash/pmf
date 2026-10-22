"""Offline unit tests (no network, no Xano): safety preflight, guarded client, S01/S02 gate,
concurrency gate harness and PMF reference values.

Run: python3 -m unittest discover -s tests/api -p 'test_offline.py'
"""
import json
import subprocess
import threading
import time
import unittest
import urllib.request

import pmf_api_tests as suite_module
import pmf_reference as ref
from concurrency import RaceResult, _overlap, gate, run_trials
from http_client import Api, NoRedirect, Response
from safety import (UnsafeEnvironment, check_canary, check_config, check_tenant_metadata,
                    fetch_tenant_metadata)

ISO_HOST = "pmf-api-test.example-tenant.xano.io"
LIVE = "xgjc-aodb-3a7q.n7e.xano.io"
GOOD = dict(
    base_url=f"https://{ISO_HOST}/api:pmf-app",
    auth_url=f"https://{ISO_HOST}/api:authcanon1",
    tenant_name="pmf-api-test",
    confirm_tenant="pmf-api-test",
    owner_token="owner-token-placeholder",
    intruder_token="intruder-token-placeholder",
)
NOW = 1_800_000_000_000
META = {"name": "pmf-api-test", "xano_domain": ISO_HOST, "ephemeral_expires_at": (NOW + 3_600_000) / 1000, "state": "ok"}


class SafetyConfig(unittest.TestCase):
    def test_good_config_passes(self):
        self.assertEqual(check_config(**GOOD), {"host": ISO_HOST, "branch": None, "auth_canonical": "authcanon1"})

    def test_branch_suffix_allowed_when_consistent(self):
        cfg = check_config(**dict(GOOD, base_url=f"https://{ISO_HOST}/api:pmf-app:v1", auth_url=f"https://{ISO_HOST}/api:authcanon1:v1"))
        self.assertEqual(cfg["branch"], "v1")

    def assert_unsafe(self, **changes):
        with self.assertRaises(UnsafeEnvironment):
            check_config(**dict(GOOD, **changes))

    def test_live_host_is_refused(self):
        self.assert_unsafe(base_url=f"https://{LIVE}/api:pmf-app", auth_url=f"https://{LIVE}/api:x")

    def test_live_auth_host_is_refused(self):
        self.assert_unsafe(auth_url=f"https://{LIVE}/api:x")

    def test_hosts_must_match(self):
        self.assert_unsafe(auth_url="https://other.xano.io/api:authcanon1")

    def test_branch_mismatch(self):
        self.assert_unsafe(base_url=f"https://{ISO_HOST}/api:pmf-app:dev")

    def test_unexpected_paths(self):
        for path in ("/api:other", "/api:pmf-app/products", "/x/api:pmf-app", "/api:pmf-apps", "/api:pmf-app:v1/extra"):
            self.assert_unsafe(base_url=f"https://{ISO_HOST}{path}")

    def test_auth_path_must_be_a_canonical(self):
        for path in ("/api:pmf-app", "/auth", "/api:a/b"):
            self.assert_unsafe(auth_url=f"https://{ISO_HOST}{path}")

    def test_https_port_credentials_query_refused(self):
        self.assert_unsafe(base_url=f"http://{ISO_HOST}/api:pmf-app")
        self.assert_unsafe(base_url=f"https://{ISO_HOST}:8443/api:pmf-app")
        self.assert_unsafe(base_url=f"https://u:p@{ISO_HOST}/api:pmf-app")
        self.assert_unsafe(base_url=f"https://{ISO_HOST}/api:pmf-app?x=1")

    def test_tenant_confirmation_and_format(self):
        self.assert_unsafe(confirm_tenant="something-else")
        self.assert_unsafe(tenant_name="../evil", confirm_tenant="../evil")

    def test_tokens(self):
        self.assert_unsafe(owner_token="")
        self.assert_unsafe(intruder_token=GOOD["owner_token"])


class TenantMetadata(unittest.TestCase):
    def check(self, **changes):
        meta = dict(META, **changes)
        return check_tenant_metadata(meta, "pmf-api-test", ISO_HOST, now_ms=NOW)

    def assert_unsafe(self, **changes):
        with self.assertRaises(UnsafeEnvironment):
            self.check(**changes)

    def test_authoritative_match_passes(self):
        self.assertTrue(self.check())

    def test_custom_domain_is_an_accepted_tenant_domain(self):
        self.assertTrue(check_tenant_metadata(dict(META, xano_domain="other.xano.io", domain=ISO_HOST), "pmf-api-test", ISO_HOST, now_ms=NOW))

    def test_name_mismatch(self):
        self.assert_unsafe(name="another-tenant")

    def test_not_ephemeral(self):
        self.assert_unsafe(ephemeral_expires_at=None)

    def test_expired_or_expiring(self):
        self.assert_unsafe(ephemeral_expires_at=(NOW - 1000) / 1000)
        self.assert_unsafe(ephemeral_expires_at=(NOW + 60_000) / 1000)

    def test_string_expiry_format(self):
        self.assertTrue(self.check(ephemeral_expires_at="2027-01-15 09:30:00+0000"))
        self.assert_unsafe(ephemeral_expires_at="not a date")

    def test_bad_state(self):
        for state in ("deleting", "failed", "error", "expired"):
            self.assert_unsafe(state=state)

    def test_host_not_owned_by_tenant(self):
        self.assert_unsafe(xano_domain="someone-else.xano.io")

    def test_tenant_on_live_host_is_refused(self):
        with self.assertRaises(UnsafeEnvironment):
            check_tenant_metadata(dict(META, xano_domain=LIVE), "pmf-api-test", LIVE, now_ms=NOW)

    def test_missing_domain(self):
        self.assert_unsafe(xano_domain=None)

    def test_malformed(self):
        with self.assertRaises(UnsafeEnvironment):
            check_tenant_metadata(None, "pmf-api-test", ISO_HOST, now_ms=NOW)


class MetadataFetch(unittest.TestCase):
    def test_uses_read_only_explicit_profile_and_workspace(self):
        seen = {}

        def runner(cmd, **kw):
            seen["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(META), stderr="")

        self.assertEqual(fetch_tenant_metadata("pmf-api-test", runner=runner), META)
        self.assertEqual(seen["cmd"], ["xano", "ephemeral", "get", "pmf-api-test", "-p", "pmf", "-w", "2", "-o", "json"])

    def test_cli_failure_and_bad_json(self):
        with self.assertRaises(UnsafeEnvironment):
            fetch_tenant_metadata("x", runner=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, stdout="", stderr="not found"))
        with self.assertRaises(UnsafeEnvironment):
            fetch_tenant_metadata("x", runner=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="oops", stderr=""))


class SafetyCanary(unittest.TestCase):
    OWNER = {"id": 1, "email": "owner@pmf-test.invalid"}
    INTRUDER = {"id": 2, "email": "intruder@pmf-test.invalid"}

    def test_synthetic_environment_passes(self):
        self.assertTrue(check_canary(self.OWNER, self.INTRUDER, {"items": [{"name": "SYNTH-x-A"}], "itemsTotal": 1}))

    def test_refusals(self):
        cases = [
            ({"id": 1, "email": "someone@example.com"}, self.INTRUDER, {"items": []}),
            (self.OWNER, self.INTRUDER, {"items": [{"name": "Real product"}]}),
            (self.OWNER, dict(self.OWNER), {"items": []}),
            ({"email": "owner@pmf-test.invalid"}, self.INTRUDER, {"items": []}),
            (self.OWNER, self.INTRUDER, {"items": [{"name": "SYNTH-a"}], "itemsTotal": 150}),
            (self.OWNER, self.INTRUDER, []),
        ]
        for owner, intruder, products in cases:
            with self.assertRaises(UnsafeEnvironment):
                check_canary(owner, intruder, products)


class GuardedClient(unittest.TestCase):
    def make(self, host=ISO_HOST, base=f"https://{ISO_HOST}/api:pmf-app"):
        calls = []
        api = Api(base, "t", [], suite_module.ROUTES, lambda *a: (calls.append(a), (200, b"{}"))[1], [], host)
        return api, calls

    def test_inventory_paths_allowed(self):
        api, calls = self.make()
        self.assertEqual(api.call("GET", "products/12/overview").status, 200)
        self.assertEqual(len(calls), 1)

    def test_paths_outside_inventory_refused(self):
        api, calls = self.make()
        for method, path in (("GET", "products/abc"), ("DELETE", "products/1"), ("GET", "../api:x/y"), ("POST", "auth/signup")):
            with self.assertRaises(UnsafeEnvironment):
                api.call(method, path)
        self.assertEqual(calls, [])

    def test_unexpected_or_live_host_refused(self):
        api, calls = self.make(host="other.xano.io")
        with self.assertRaises(UnsafeEnvironment):
            api.call("GET", "products")
        api, calls = self.make(host=LIVE, base=f"https://{LIVE}/api:pmf-app")
        with self.assertRaises(UnsafeEnvironment):
            api.call("GET", "products")
        self.assertEqual(calls, [])

    def test_redirects_are_refused(self):
        req = urllib.request.Request(f"https://{ISO_HOST}/api:pmf-app/products", method="POST")
        with self.assertRaises(UnsafeEnvironment):
            NoRedirect().redirect_request(req, None, 307, "Temporary Redirect", {}, f"https://{LIVE}/api:pmf-app/products")


class FakeXano:
    """In-memory responder for the gate tests. Sweeps target id 999999999."""

    def __init__(self, anon_status=401, intruder_status=403, anon_override=None, intruder_override=None):
        self.anon_status, self.intruder_status = anon_status, intruder_status
        self.anon_override, self.intruder_override = anon_override, intruder_override

    def __call__(self, method, url, headers, data):
        token = headers.get("Authorization", "").replace("Bearer ", "")
        path = url.split("/api:", 1)[1].split("/", 1)[1].split("?")[0]
        if path == "auth/me":
            who = "owner" if token == GOOD["owner_token"] else "intruder"
            return 200, json.dumps({"id": 1 if who == "owner" else 2, "email": f"{who}@pmf-test.invalid"}).encode()
        if method == "GET" and path == "products" and token == GOOD["owner_token"]:
            return 200, json.dumps({"items": [], "itemsTotal": 0}).encode()
        if not token:
            status = self.anon_override.get((method, path), self.anon_status) if self.anon_override else self.anon_status
            return status, json.dumps({"code": "ERROR_CODE_UNAUTHORIZED", "message": "Unauthorized"}).encode()
        if token == GOOD["intruder_token"]:
            status = self.intruder_override.get((method, path), self.intruder_status) if self.intruder_override else self.intruder_status
            return status, json.dumps({"code": "ERROR_CODE_ACCESS_DENIED", "message": "NOT_OWNER: denied"}).encode()
        return 500, b'{"message": "unexpected owner write in gate test"}'


ENV = {
    "PMF_TEST_BASE_URL": GOOD["base_url"], "PMF_TEST_AUTH_URL": GOOD["auth_url"],
    "PMF_TEST_TENANT_NAME": GOOD["tenant_name"], "PMF_TEST_OWNER_TOKEN": GOOD["owner_token"],
    "PMF_TEST_INTRUDER_TOKEN": GOOD["intruder_token"],
}


def meta_provider(name):
    return dict(META, name=name, ephemeral_expires_at=time.time() + 3600)


class FixtureReached(Exception):
    pass


class SecurityGate(unittest.TestCase):
    def setUp(self):
        self.fixture_calls = 0
        original = suite_module.Suite.build_fixture

        def fake_fixture(suite_self):
            self.fixture_calls += 1
            raise FixtureReached()

        suite_module.Suite.build_fixture = fake_fixture
        self.addCleanup(setattr, suite_module.Suite, "build_fixture", original)

    def run_with(self, server):
        lines = []
        code, suite = suite_module.run_suite(ENV, GOOD["tenant_name"], transport=server, metadata_provider=meta_provider, out=lines.append)
        return code, suite, lines

    def assert_only_canary_and_sweeps(self, suite):
        for method, path, has_token, token in suite.requests:
            canary = (method, path) in (("GET", "auth/me"), ("GET", "products"))
            sweep = str(suite_module.MISSING_ID) in path or path == "products"
            self.assertTrue(canary or (sweep and token != GOOD["owner_token"]), f"unexpected request {method} {path}")

    def test_s01_failure_aborts_before_fixture(self):
        code, suite, lines = self.run_with(FakeXano(anon_override={("POST", "products"): 200}))
        self.assertEqual(code, suite_module.GATE_EXIT)
        self.assertEqual(self.fixture_calls, 0)
        self.assert_only_canary_and_sweeps(suite)
        self.assertTrue(any("ABORT (gate)" in line for line in lines))

    def test_s02_failure_aborts_before_fixture(self):
        code, suite, _ = self.run_with(FakeXano(intruder_override={("PATCH", f"customers/{suite_module.MISSING_ID}"): 400}))
        self.assertEqual(code, suite_module.GATE_EXIT)
        self.assertEqual(self.fixture_calls, 0)
        self.assert_only_canary_and_sweeps(suite)

    def test_gate_ignores_only_filter(self):
        lines = []
        code, suite = suite_module.run_suite(ENV, GOOD["tenant_name"], transport=FakeXano(anon_status=200),
                                             metadata_provider=meta_provider, only=["W01"], out=lines.append)
        self.assertEqual(code, suite_module.GATE_EXIT)
        self.assertEqual(self.fixture_calls, 0)

    def test_passing_gate_reaches_fixture(self):
        code, suite, lines = self.run_with(FakeXano())
        self.assertEqual(self.fixture_calls, 1)
        self.assertEqual([r[1] for r in suite.results], ["PASS", "PASS"])
        self.assertEqual(code, 1)  # fixture stub raised; nothing beyond the gate ran
        self.assertTrue(any(line.startswith("FIXTURE FAILED") for line in lines))

    def test_preflight_failure_sends_no_request(self):
        calls = []
        code, _ = suite_module.run_suite(ENV, GOOD["tenant_name"], transport=lambda *a: calls.append(a),
                                         metadata_provider=lambda name: dict(META, xano_domain="elsewhere.xano.io"), out=lambda *_: None)
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])

    def test_live_configuration_sends_no_request(self):
        calls = []
        env = dict(ENV, PMF_TEST_BASE_URL=f"https://{LIVE}/api:pmf-app", PMF_TEST_AUTH_URL=f"https://{LIVE}/api:xHMmrw_d")
        code, _ = suite_module.run_suite(env, GOOD["tenant_name"], transport=lambda *a: calls.append(a),
                                         metadata_provider=meta_provider, out=lambda *_: None)
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])

    def test_canary_failure_aborts_before_sweeps(self):
        def server(method, url, headers, data):
            if url.endswith("auth/me"):
                return 200, json.dumps({"id": 7, "email": "real.person@example.com"}).encode()
            return 200, b'{"items": []}'
        code, suite, _ = self.run_with(server)
        self.assertEqual(code, 2)
        self.assertTrue(all(m == "GET" for m, *_ in suite.requests))


class ConcurrencyGate(unittest.TestCase):
    def test_overlapping_trials_pass(self):
        r = run_trials("t", 5, lambda i: {}, [lambda ctx: (time.sleep(0.02), Response(200, {}))[1]] * 2, lambda ctx, rs: None)
        self.assertIsNone(gate(r))

    def test_any_violation_fails(self):
        r = run_trials("t", 5, lambda i: {"i": i}, [lambda ctx: (time.sleep(0.01), Response(200, {}))[1]] * 2,
                       lambda ctx, rs: "broken" if ctx["i"] == 3 else None)
        self.assertIn("INVARIANT VIOLATED", gate(r))

    def test_non_overlapping_trials_are_inconclusive(self):
        r = RaceResult("t")
        r.trials = [{"statuses": [200, 400], "overlap": False, "intervals": [(0, 1), (2, 3)]}] * 4 \
            + [{"statuses": [200, 400], "overlap": True, "intervals": [(0, 2), (1, 3)]}]
        self.assertIn("INCONCLUSIVE", gate(r))

    def test_overlap_detection(self):
        self.assertTrue(_overlap([(0, 2), (1, 3)]))
        self.assertFalse(_overlap([(0, 1), (2, 3)]))
        self.assertFalse(_overlap([(0, 1), (1, 2)]))

    def test_client_overlap_is_not_server_proof(self):
        # Documented limitation: server-side serialization still shows client-side overlap.
        lock = threading.Lock()

        def serialized(ctx):
            with lock:
                time.sleep(0.01)
                return Response(200, {})

        r = run_trials("t", 3, lambda i: {}, [serialized] * 2, lambda ctx, rs: None)
        self.assertGreater(r.overlap_ratio, 0)

    def test_request_errors_fail(self):
        def boom(ctx):
            raise RuntimeError("network")

        r = run_trials("t", 3, lambda i: {}, [boom, boom], lambda ctx, rs: None)
        self.assertIn("INVARIANT VIOLATED", gate(r))


class InventoryConsistency(unittest.TestCase):
    def test_run_order_and_routes(self):
        ids = [t[0] for t in suite_module.TESTS]
        self.assertEqual(sorted(suite_module.ORDER_PRE + suite_module.RUN_ORDER), sorted(ids))
        self.assertEqual(len(suite_module.ROUTES), 48)
        advertised = {f"S0{i}" for i in (1, 2, 4, 5, 6, 7)} | {f"M0{i}" for i in range(1, 8)} | {f"R0{i}" for i in range(1, 6)} \
            | {f"W{i:02d}" for i in range(1, 12)} | {f"P0{i}" for i in range(1, 10)} | {f"E0{i}" for i in range(0, 10)} \
            | {f"I0{i}" for i in range(1, 6)} | {f"V0{i}" for i in range(1, 6)} | {f"C0{i}" for i in range(1, 5)} | {"X01", "X02"}
        self.assertEqual(set(ids), advertised)
        self.assertEqual({m[0] for m in suite_module.MANUAL}, {"S03", "S08", "S09"})


class ReferenceScoring(unittest.TestCase):
    def test_fixture_w1(self):
        c = ref.count_rows(ref.W1_ROWS)
        self.assertEqual((c["eligible_count"], c["invited_count"], c["valid_response_count"]), (5, 4, 3))
        self.assertEqual((c["very_count"], c["somewhat_count"], c["not_count"]), (1, 1, 1))
        r = ref.compute(c)
        self.assertAlmostEqual(r["pmf_percent"], 100 / 3, places=9)
        self.assertEqual(r["invited_response_rate"], 0.5)
        self.assertEqual(c["manual_valid_count"], 1)
        self.assertTrue(r["small_sample"])

    def test_segments(self):
        a1 = ref.compute(ref.count_rows([r for r in ref.W1_ROWS if r["segment"] == "A1"]))
        a2 = ref.compute(ref.count_rows([r for r in ref.W1_ROWS if r["segment"] == "A2"]))
        un = ref.compute(ref.count_rows([r for r in ref.W1_ROWS if r["segment"] is None]))
        self.assertEqual(a1["pmf_percent"], 50.0)
        self.assertIsNone(a2["pmf_percent"])
        self.assertEqual(un["pmf_percent"], 0.0)

    def test_zero_denominator_is_null(self):
        self.assertIsNone(ref.compute(ref.count_rows([{"invited_at": None, "responded_at": None, "disappointment_level": None}]))["pmf_percent"])

    def test_incomplete_never_counts(self):
        c = ref.count_rows([{"responded_at": 1, "disappointment_level": None}, {"responded_at": None, "disappointment_level": "very"}])
        self.assertEqual((c["valid_response_count"], c["incomplete_response_count"], c["anomaly_count"]), (0, 1, 1))

    def test_threshold_is_thirty(self):
        rows = [{"invited_at": 1, "responded_at": 1, "disappointment_level": "very"}] * 30
        self.assertFalse(ref.compute(ref.count_rows(rows))["small_sample"])
        self.assertTrue(ref.compute(ref.count_rows(rows[:29]))["small_sample"])


if __name__ == "__main__":
    unittest.main()
