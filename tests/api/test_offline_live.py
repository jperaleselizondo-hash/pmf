"""Offline tests (no network, no Xano) for the authorized live-workspace mode, cleanup and deployment checks.

Run: python3 -m unittest discover -s tests/api -p 'test_offline*.py'
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import urllib.parse

import cleanup_live
import live_target as live
import pmf_api_tests as suite_module
from http_client import Api
from safety import UnsafeEnvironment

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "static"))
import check_dry_run  # noqa: E402
import compare_readback  # noqa: E402

OWNER_ID = 7
ENV = {
    "PMF_TEST_BASE_URL": live.BASE_URL, "PMF_TEST_AUTH_URL": live.AUTH_URL,
    "PMF_TEST_OWNER_TOKEN": "owner-placeholder", "PMF_TEST_INTRUDER_TOKEN": "intruder-placeholder",
    "PMF_XANO_META_TOKEN": "meta-placeholder", "PMF_TEST_OWNER_ID": str(OWNER_ID),
}
TABLE_IDS = {name: i + 10 for i, name in enumerate(live.BUSINESS_TABLES)}
TABLE_IDS["user"] = 99


def fake_cli(instance=live.LIVE_INSTANCE, ws_id=2, ws_name="pmf", auth_canon=live.AUTH_CANONICAL, deployed=True, calls=None):
    def runner(cmd, **kw):
        if calls is not None:
            calls.append(cmd)
        assert cmd[0] == "xano"
        if cmd[1:3] == ["profile", "me"]:
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"extras": {"instance": {"name": instance}}}), "")
        if cmd[1:3] == ["workspace", "get"]:
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"id": ws_id, "name": ws_name}), "")
        if cmd[1:3] == ["workspace", "pull"]:
            out = pathlib.Path(cmd[cmd.index("-d") + 1])
            (out / "api" / "authentication").mkdir(parents=True)
            (out / "api" / "authentication" / "authentication.xs").write_text(f'api_group Authentication {{\n  canonical = "{auth_canon}"\n}}\n')
            if deployed:
                (out / "api" / "pmf_app").mkdir(parents=True)
                (out / "api" / "pmf_app" / "api_group.xs").write_text('api_group "PMF App" {\n  canonical = "pmf-app"\n}\n')
            return subprocess.CompletedProcess(cmd, 0, "Pulled", "")
        raise AssertionError(f"unexpected CLI command {cmd}")
    return runner


class FakeMeta:
    """In-memory Metadata API (workspace 2) with request log."""

    def __init__(self, rows=None):
        self.rows = {name: [dict(r) for r in (rows or {}).get(name, [])] for name in TABLE_IDS}
        self.log = []

    def __call__(self, method, url, headers, data):
        parts = urllib.parse.urlsplit(url)
        assert parts.hostname == live.LIVE_HOST and parts.path.startswith("/api:meta/workspace/2/table")
        q = dict(urllib.parse.parse_qsl(parts.query))
        path = parts.path[len("/api:meta"):]
        self.log.append((method, path))
        segs = path.strip("/").split("/")
        if len(segs) == 3:
            return 200, json.dumps({"items": [{"id": i, "name": n} for n, i in TABLE_IDS.items()]}).encode()
        name = next(n for n, i in TABLE_IDS.items() if i == int(segs[3]))
        if method == "DELETE":
            self.rows[name] = [r for r in self.rows[name] if r["id"] != int(segs[5])]
            return 200, b"{}"
        page, per = int(q.get("page", 1)), int(q.get("per_page", 50))
        items = self.rows[name][(page - 1) * per: page * per]
        nxt = page + 1 if page * per < len(self.rows[name]) else None
        return 200, json.dumps({"items": items, "itemsTotal": len(self.rows[name]), "nextPage": nxt}).encode()


def synthetic_rows():
    return {
        "products": [{"id": 1, "name": "SYNTH-run-A", "owner_user_id": OWNER_ID}],
        "segments": [{"id": 2, "product_id": 1}],
        "customers": [{"id": 3, "product_id": 1, "segment_id": 2, "name": "SYNTH C1", "email": "c1@pmf-test.invalid"},
                      {"id": 4, "product_id": 1, "segment_id": None, "name": None, "email": None}],
        "interviews": [{"id": 5, "customer_id": 3}],
        "survey_waves": [{"id": 6, "product_id": 1}],
        "survey_participations": [{"id": 7, "survey_wave_id": 6, "customer_id": 3}],
        "insights": [{"id": 8, "product_id": 1}],
        "insight_evidence": [{"id": 9, "insight_id": 8, "interview_id": 5, "survey_participation_id": None}],
        "hypotheses": [{"id": 10, "insight_id": 8}],
        "experiments": [{"id": 11, "hypothesis_id": 10}],
    }


class LiveConfig(unittest.TestCase):
    def test_good(self):
        self.assertEqual(live.check_live_config(ENV, live.CONFIRM_PHRASE), OWNER_ID)

    def test_refusals(self):
        cases = [
            (ENV, "yes"),
            (dict(ENV, PMF_TEST_BASE_URL=live.BASE_URL + ":dev"), live.CONFIRM_PHRASE),
            (dict(ENV, PMF_TEST_BASE_URL="https://other.xano.io/api:pmf-app"), live.CONFIRM_PHRASE),
            (dict(ENV, PMF_TEST_AUTH_URL=f"https://{live.LIVE_HOST}/api:other"), live.CONFIRM_PHRASE),
            (dict(ENV, PMF_XANO_META_TOKEN=""), live.CONFIRM_PHRASE),
            (dict(ENV, PMF_TEST_OWNER_ID="abc"), live.CONFIRM_PHRASE),
            (dict(ENV, PMF_TEST_INTRUDER_TOKEN=ENV["PMF_TEST_OWNER_TOKEN"]), live.CONFIRM_PHRASE),
        ]
        for env, phrase in cases:
            with self.assertRaises(UnsafeEnvironment):
                live.check_live_config(env, phrase)

    def test_cli_identity(self):
        calls = []
        live.verify_cli_identity(fake_cli(calls=calls))
        self.assertTrue(all("-p" in c and c[c.index("-p") + 1] == "pmf" for c in calls))
        self.assertTrue(any("-w" in c and c[c.index("-w") + 1] == "2" for c in calls))
        for bad in (dict(instance="other-instance"), dict(ws_id=1), dict(ws_name="goodz")):
            with self.assertRaises(UnsafeEnvironment):
                live.verify_cli_identity(fake_cli(**bad))

    def test_canonicals(self):
        calls = []
        groups = live.verify_canonicals(fake_cli(calls=calls))
        self.assertEqual(groups["PMF App"], "pmf-app")
        pull = calls[-1]
        self.assertNotIn("--env", pull)
        self.assertNotIn("--records", pull)
        with self.assertRaises(UnsafeEnvironment):
            live.verify_canonicals(fake_cli(deployed=False))
        with self.assertRaises(UnsafeEnvironment):
            live.verify_canonicals(fake_cli(auth_canon="somethingelse"))


class MetaGuard(unittest.TestCase):
    def test_paths_are_pinned_to_workspace_2(self):
        meta = live.MetaClient("t", FakeMeta())
        for method, path in (("GET", "/workspace/1/table"), ("GET", "/workspace"), ("DELETE", "/workspace/2/table/10"),
                             ("PUT", "/workspace/2/table/10/content/1"), ("GET", "/workspace/2/table/10/truncate")):
            with self.assertRaises(UnsafeEnvironment):
                meta._call(method, path)

    def test_deletes_need_explicit_table_permission(self):
        fake = FakeMeta(synthetic_rows())
        meta = live.MetaClient("t", fake)
        meta.resolve_tables()
        with self.assertRaises(UnsafeEnvironment):
            meta.delete("products", 1)
        with self.assertRaises(UnsafeEnvironment):
            meta.rows("user")
        with self.assertRaises(UnsafeEnvironment):
            meta.count("user")

    def test_counts_and_paging(self):
        rows = synthetic_rows()
        rows["customers"] = [{"id": i, "product_id": 1, "name": None, "email": None} for i in range(1, 1201)]
        meta = live.MetaClient("t", FakeMeta(rows))
        meta.resolve_tables()
        self.assertEqual(len(meta.rows("customers")), 1200)
        self.assertEqual(meta.counts()["customers"], 1200)


class SyntheticVerification(unittest.TestCase):
    def test_all_synthetic(self):
        problems, plan = live.verify_synthetic(synthetic_rows(), OWNER_ID)
        self.assertEqual(problems, [])
        self.assertEqual(plan["experiments"], [11])

    def test_real_data_stops(self):
        variants = []
        r = synthetic_rows(); r["products"].append({"id": 50, "name": "My real product", "owner_user_id": OWNER_ID}); variants.append(r)
        r = synthetic_rows(); r["products"][0]["owner_user_id"] = 99; variants.append(r)
        r = synthetic_rows(); r["customers"][0]["email"] = "person@example.com"; variants.append(r)
        r = synthetic_rows(); r["customers"][0]["name"] = "Real Person"; variants.append(r)
        r = synthetic_rows(); r["interviews"].append({"id": 51, "customer_id": 999}); variants.append(r)
        r = synthetic_rows(); r["experiments"].append({"id": 52, "hypothesis_id": 999}); variants.append(r)
        for rows in variants:
            problems, _ = live.verify_synthetic(rows, OWNER_ID)
            self.assertTrue(problems)


class LiveRunner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        original = suite_module.Suite.build_fixture
        self.fixture_calls = 0

        def fake_fixture(s):
            self.fixture_calls += 1
            s.owner.call("POST", "products", {"name": f"SYNTH-{s.tag}-A"})
            raise RuntimeError("stop after first fixture write")

        suite_module.Suite.build_fixture = fake_fixture
        self.addCleanup(setattr, suite_module.Suite, "build_fixture", original)

    def server(self, meta, anon=401, intruder=403, owner_products=None, intruder_email="intruder@pmf-test.invalid", owner_id=OWNER_ID):
        def transport(method, url, headers, data):
            host = urllib.parse.urlsplit(url).hostname
            assert host == live.LIVE_HOST
            if "/api:meta/" in url:
                return meta(method, url, headers, data)
            token = headers.get("Authorization", "").replace("Bearer ", "")
            path = url.split("/api:", 1)[1].split("/", 1)[1].split("?")[0]
            if path == "auth/me":
                if token == ENV["PMF_TEST_OWNER_TOKEN"]:
                    return 200, json.dumps({"id": owner_id, "email": "owner@real.example"}).encode()
                return 200, json.dumps({"id": 8, "email": intruder_email}).encode()
            if token == ENV["PMF_TEST_OWNER_TOKEN"]:
                if method == "GET" and path == "products":
                    return 200, json.dumps({"items": owner_products or [], "itemsTotal": 0}).encode()
                if method == "POST" and path == "products":
                    return 200, json.dumps({"id": 123, "name": "SYNTH-x"}).encode()
            if not token:
                return anon, b'{"message": "Unauthorized"}'
            return intruder, b'{"message": "NOT_OWNER: denied"}'
        return transport

    def run_live(self, transport, meta_fake, phrase=live.CONFIRM_PHRASE, cli=None):
        lines = []
        meta = live.MetaClient(ENV["PMF_XANO_META_TOKEN"], meta_fake)
        code, suite = suite_module.run_suite(ENV, target="live-pmf", confirm_live=phrase, transport=transport,
                                             cli_runner=cli or fake_cli(), meta_client=meta,
                                             ledger_path=pathlib.Path(self.tmp.name) / "ledger.jsonl", out=lines.append)
        return code, suite, lines

    def test_requires_confirmation_and_sends_nothing(self):
        meta = FakeMeta()
        calls = []
        code, _, _ = self.run_live(lambda *a: calls.append(a), meta, phrase="please")
        self.assertEqual((code, calls, meta.log), (2, [], []))

    def test_wrong_workspace_identity_aborts(self):
        meta = FakeMeta()
        code, _, _ = self.run_live(self.server(meta), meta, cli=fake_cli(ws_name="goodz"))
        self.assertEqual(code, 2)

    def test_non_empty_tables_abort_before_any_api_request(self):
        meta = FakeMeta({"products": [{"id": 1, "name": "Real", "owner_user_id": OWNER_ID}]})
        calls = []
        code, _, _ = self.run_live(lambda *a: calls.append(a) or (200, b"{}"), meta)
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])

    def test_wrong_owner_or_real_intruder_abort_at_canary(self):
        meta = FakeMeta()
        for kwargs in (dict(owner_id=99), dict(intruder_email="person@example.com")):
            code, suite, _ = self.run_live(self.server(meta, **kwargs), meta)
            self.assertEqual(code, 2)
            self.assertTrue(all(m == "GET" for m, *_ in suite.requests))

    def test_gate_failure_in_live_mode_aborts_before_fixture(self):
        meta = FakeMeta()
        code, suite, lines = self.run_live(self.server(meta, anon=200), meta)
        self.assertEqual(code, suite_module.GATE_EXIT)
        self.assertEqual(self.fixture_calls, 0)
        self.assertTrue(any("RECOVERY" in line for line in lines))

    def test_sweep_side_effects_abort_before_fixture(self):
        meta = FakeMeta()
        original_counts = live.MetaClient.counts
        state = {"n": 0}

        def counts(self_):
            state["n"] += 1
            result = original_counts(self_)
            if state["n"] >= 2:
                result["products"] = 1
            return result

        live.MetaClient.counts = counts
        self.addCleanup(setattr, live.MetaClient, "counts", original_counts)
        code, _, _ = self.run_live(self.server(meta), meta)
        self.assertEqual(code, suite_module.GATE_EXIT)
        self.assertEqual(self.fixture_calls, 0)

    def test_passing_gate_reaches_fixture_and_ledger_records_writes(self):
        meta = FakeMeta()
        code, suite, lines = self.run_live(self.server(meta), meta)
        self.assertEqual(self.fixture_calls, 1)
        self.assertEqual(code, 1)
        ledger = (pathlib.Path(self.tmp.name) / "ledger.jsonl").read_text().splitlines()
        self.assertEqual([json.loads(x)["table"] for x in ledger], ["products"])
        self.assertTrue(any("RECOVERY" in line for line in lines))

    def test_isolated_mode_still_denies_live_host(self):
        api = Api(live.BASE_URL, "t", [], suite_module.ROUTES, lambda *a: (200, b"{}"), [], live.LIVE_HOST)
        with self.assertRaises(UnsafeEnvironment):
            api.call("GET", "products")
        code, _ = suite_module.run_suite(dict(ENV, PMF_TEST_TENANT_NAME="t1"), "t1", transport=lambda *a: (200, b"{}"),
                                         metadata_provider=lambda n: {}, out=lambda *_: None)
        self.assertEqual(code, 2)

    def test_confirm_live_rejected_in_isolated_mode(self):
        code, _ = suite_module.run_suite(ENV, "t1", confirm_live=live.CONFIRM_PHRASE, transport=lambda *a: (200, b"{}"),
                                         metadata_provider=lambda n: {}, out=lambda *_: None)
        self.assertEqual(code, 2)


class Cleanup(unittest.TestCase):
    def transport(self, meta, intruder_email="intruder@pmf-test.invalid", intruder_id=8):
        def t(method, url, headers, data):
            if "/api:meta/" in url:
                return meta(method, url, headers, data)
            assert url == f"{live.AUTH_URL}/auth/me"
            return 200, json.dumps({"id": intruder_id, "email": intruder_email}).encode()
        return t

    def do_cleanup(self, meta, **kw):
        lines = []
        transport = kw.pop("transport", None) or self.transport(meta)
        code = cleanup_live.run_cleanup(ENV, kw.pop("confirm", live.CLEANUP_PHRASE), cli_runner=fake_cli(),
                                        meta=live.MetaClient("t", meta), transport=transport, out=lines.append, **kw)
        return code, lines

    def test_wrong_phrase_deletes_nothing(self):
        meta = FakeMeta(synthetic_rows())
        code, _ = self.do_cleanup(meta, confirm="yes", execute=True)
        self.assertEqual(code, 2)
        self.assertFalse(any(m == "DELETE" for m, _ in meta.log))

    def test_dry_run_deletes_nothing(self):
        meta = FakeMeta(synthetic_rows())
        code, lines = self.do_cleanup(meta)
        self.assertEqual(code, 0)
        self.assertFalse(any(m == "DELETE" for m, _ in meta.log))
        self.assertTrue(any(line.startswith("DRY RUN") for line in lines))

    def test_real_record_stops_everything(self):
        rows = synthetic_rows()
        rows["products"].append({"id": 60, "name": "Real product", "owner_user_id": OWNER_ID})
        meta = FakeMeta(rows)
        code, lines = self.do_cleanup(meta, execute=True, remove_test_user=True)
        self.assertEqual(code, 2)
        self.assertFalse(any(m == "DELETE" for m, _ in meta.log))
        self.assertTrue(lines[0].startswith("STOP"))

    def test_execute_deletes_children_first_then_only_the_test_user(self):
        rows = synthetic_rows()
        meta = FakeMeta(rows)
        meta.rows["user"] = [{"id": OWNER_ID}, {"id": 8}]
        code, lines = self.do_cleanup(meta, execute=True, remove_test_user=True)
        self.assertEqual(code, 0)
        deleted = [path for m, path in meta.log if m == "DELETE"]
        order = [next(n for n, i in TABLE_IDS.items() if i == int(p.split("/")[4])) for p in deleted]
        collapsed = [t for i, t in enumerate(order) if i == 0 or order[i - 1] != t]
        self.assertEqual(collapsed, live.BUSINESS_TABLES + ["user"])
        self.assertEqual(len(deleted), sum(len(v) for v in synthetic_rows().values()) + 1)
        self.assertEqual([r["id"] for r in meta.rows["user"]], [OWNER_ID])
        self.assertTrue(lines[-1].startswith("VERIFIED"))

    def test_owner_or_real_account_is_never_removed_as_test_user(self):
        for kwargs in (dict(intruder_id=OWNER_ID), dict(intruder_email="person@example.com")):
            meta = FakeMeta(synthetic_rows())
            code, _ = self.do_cleanup(meta, execute=True, remove_test_user=True, transport=self.transport(FakeMeta(), **kwargs))
            self.assertEqual(code, 2)
            self.assertFalse(any(m == "DELETE" for m, _ in meta.log))

    def test_reports_incomplete_when_tables_not_empty(self):
        class StickyProducts(FakeMeta):
            def __call__(self, method, url, headers, data):
                if method == "DELETE" and f"/table/{TABLE_IDS['products']}/" in url:
                    self.log.append((method, url))
                    return 200, b"{}"  # server claims success but the row remains
                return super().__call__(method, url, headers, data)

        meta = StickyProducts(synthetic_rows())
        code, lines = self.do_cleanup(meta, execute=True)
        self.assertEqual(code, 4)
        self.assertTrue(lines[-1].startswith("INCOMPLETE"))


class DeploymentChecks(unittest.TestCase):
    def preview(self, lines):
        return "=== Push Preview: workspace 2 ===\n\n--- Changes ---\n\n" + "\n".join(lines) + "\n"

    def good_lines(self):
        return ["  CREATE           api_group          PMF App"] + \
               [f"  CREATE           query              route{i}" for i in range(48)] + \
               [f"  CREATE           function           pmf/f{i}" for i in range(34)]

    def test_expected_objects_from_sources(self):
        self.assertEqual(check_dry_run.expected_objects(), {"api_group": 1, "query": 48, "function": 34})

    def test_good_preview_passes(self):
        problems, by_type, unknown = check_dry_run.check(self.preview(self.good_lines()), check_dry_run.expected_objects())
        self.assertEqual((problems, unknown), ([], {}))

    def test_bad_previews_fail(self):
        expected = check_dry_run.expected_objects()
        variants = [
            self.good_lines() + ["  UPDATE           table              customers"],
            self.good_lines()[:-1],
            self.good_lines() + ["  CREATE           query              auth/signup"],
            [line.replace("CREATE", "DELETE", 1) if i == 3 else line for i, line in enumerate(self.good_lines())],
        ]
        for lines in variants:
            problems, _, _ = check_dry_run.check(self.preview(lines), expected)
            self.assertTrue(problems)

    def test_readback_comparator(self):
        with tempfile.TemporaryDirectory() as tmp:
            after, before = pathlib.Path(tmp, "after"), pathlib.Path(tmp, "before")
            for f in compare_readback.APP.rglob("*.xs"):
                rel = f.relative_to(compare_readback.APP)
                target = after / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f.read_text().replace("\n}\n", '\n  guid = "abc"\n}\n', 1))
            (before / "table").mkdir(parents=True)
            (after / "table").mkdir(parents=True)
            (before / "table" / "user.xs").write_text("table user {}\n")
            (after / "table" / "user.xs").write_text("table user {}\n")
            sys_argv = sys.argv
            try:
                sys.argv = ["x", str(after), "--baseline", str(before)]
                self.assertEqual(compare_readback.main(), 0)
                (after / "table" / "user.xs").write_text("table user { changed }\n")
                self.assertEqual(compare_readback.main(), 1)
            finally:
                sys.argv = sys_argv


if __name__ == "__main__":
    unittest.main()
