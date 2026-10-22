"""Offline tests (no network, no Xano) for the authorized live-workspace mode, cleanup and deployment checks.

Run: python3 -m unittest discover -s tests/api -p 'test_offline*.py'
"""
import json
import re
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
    """In-memory Metadata API (workspace 2) following the documented page shape, with request log.

    `faults` lets tests corrupt replies: a callable (method, path, query, status, body) -> (status, body).
    `delete_status` is the status returned by DELETE (the row is removed for 200/204 unless `sticky`).
    """

    def __init__(self, rows=None, faults=None, delete_status=200, sticky=()):
        self.rows = {name: [dict(r) for r in (rows or {}).get(name, [])] for name in TABLE_IDS}
        self.log = []
        self.faults = faults
        self.delete_status = delete_status
        self.sticky = set(sticky)

    @staticmethod
    def page(items, page, per):
        chunk = items[(page - 1) * per: page * per]
        nxt = page + 1 if page * per < len(items) else None
        return {"items": chunk, "itemsReceived": len(chunk), "curPage": page, "nextPage": nxt,
                "prevPage": page - 1 or None, "offset": (page - 1) * per, "perPage": per, "itemsTotal": len(items)}

    def respond(self, method, path, q):
        segs = path.strip("/").split("/")
        page, per = int(q.get("page", 1)), int(q.get("per_page", 50))
        if len(segs) == 3:
            return 200, self.page([{"id": i, "name": n} for n, i in TABLE_IDS.items()], page, per)
        name = next(n for n, i in TABLE_IDS.items() if i == int(segs[3]))
        if len(segs) == 6:
            row_id = int(segs[5])
            exists = any(r["id"] == row_id for r in self.rows[name])
            if method == "DELETE":
                if self.delete_status in (200, 204) and name not in self.sticky:
                    self.rows[name] = [r for r in self.rows[name] if r["id"] != row_id]
                return self.delete_status, (None if self.delete_status == 204 else {})
            return (200, {"id": row_id}) if exists else (404, {"message": "not found"})
        return 200, self.page(self.rows[name], page, per)

    def __call__(self, method, url, headers, data):
        parts = urllib.parse.urlsplit(url)
        assert parts.hostname == live.LIVE_HOST and parts.path.startswith("/api:meta/workspace/2/table")
        q = dict(urllib.parse.parse_qsl(parts.query))
        path = parts.path[len("/api:meta"):]
        self.log.append((method, path))
        status, body = self.respond(method, path, q)
        if self.faults:
            status, body = self.faults(method, path, q, status, body)
        raw = b"" if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        return status, raw


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
                meta._request(method, path)

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


class MetaFailClosed(unittest.TestCase):
    """Malformed, contradictory or incomplete Metadata API replies must stop testing and cleanup."""

    def client(self, fault, rows=None):
        meta = live.MetaClient("t", FakeMeta(rows if rows is not None else synthetic_rows(), faults=fault))
        return meta

    def content_fault(self, mutate):
        def fault(method, path, q, status, body):
            if method == "GET" and path.endswith("/content") and isinstance(body, dict):
                body = dict(body)
                mutate(body, q)
            return status, body
        return fault

    def assert_stops(self, call):
        with self.assertRaises(UnsafeEnvironment):
            call()

    def test_count_requires_valid_items_total(self):
        for mutate in (lambda b, q: b.pop("itemsTotal"), lambda b, q: b.update(itemsTotal=None),
                       lambda b, q: b.update(itemsTotal="3"), lambda b, q: b.update(itemsTotal=-1),
                       lambda b, q: b.update(itemsTotal=True), lambda b, q: b.update(itemsTotal=1.5)):
            meta = self.client(self.content_fault(mutate))
            meta.resolve_tables()
            self.assert_stops(lambda: meta.count("products"))
            self.assert_stops(meta.counts)

    def test_count_rejects_contradictions(self):
        cases = [
            lambda b, q: b.update(itemsTotal=0),                       # rows returned but total 0
            lambda b, q: b.update(items=[]),                           # total > 0 but no rows
            lambda b, q: b.update(nextPage=None, itemsTotal=5),        # more pages implied but none offered
        ]
        for mutate in cases:
            meta = self.client(self.content_fault(mutate))
            meta.resolve_tables()
            self.assert_stops(lambda: meta.count("products"))

    def test_rows_reject_malformed_items(self):
        for mutate in (lambda b, q: b.pop("items"), lambda b, q: b.update(items={}), lambda b, q: b.update(items=["x"]),
                       lambda b, q: b.update(items=[{"name": "no id"}]), lambda b, q: b.update(items=[{"id": "1"}])):
            meta = self.client(self.content_fault(mutate))
            meta.resolve_tables()
            self.assert_stops(lambda: meta.rows("products"))

    def test_rows_reject_incomplete_or_inconsistent_pagination(self):
        rows = synthetic_rows()
        rows["customers"] = [{"id": i, "product_id": 1, "name": None, "email": None} for i in range(1, 1201)]
        cases = [
            lambda b, q: b.update(nextPage=None) if q.get("page") == "1" else None,            # stops early
            lambda b, q: b.update(itemsTotal=1300) if q.get("page") == "2" else None,          # total changes
            lambda b, q: b.update(items=b["items"][:-1]) if q.get("page") == "3" else None,    # short page
            lambda b, q: b.update(items=b["items"] + b["items"][:1]) if q.get("page") == "2" else None,  # oversized
            lambda b, q: b.update(nextPage=5) if q.get("page") == "1" else None,               # skips pages
        ]
        for mutate in cases:
            meta = self.client(self.content_fault(mutate), rows)
            meta.resolve_tables()
            self.assert_stops(lambda: meta.rows("customers"))

    def test_rows_reject_duplicate_ids(self):
        rows = synthetic_rows()
        rows["customers"] = [{"id": 1, "product_id": 1}, {"id": 1, "product_id": 1}]
        meta = self.client(None, rows)
        meta.resolve_tables()
        self.assert_stops(lambda: meta.rows("customers"))

    def test_non_json_and_non_200_stop(self):
        for fault in (lambda m, p, q, st, b: (st, b"<html>") if p.endswith("/content") else (st, b),
                      lambda m, p, q, st, b: (500, b) if p.endswith("/content") else (st, b),
                      lambda m, p, q, st, b: (302, b) if p.endswith("/content") else (st, b)):
            meta = self.client(fault)
            meta.resolve_tables()
            self.assert_stops(lambda: meta.count("products"))

    def test_table_listing_must_be_complete_and_well_formed(self):
        for fault in (lambda m, p, q, st, b: (st, {"items": b["items"]}) if p.endswith("/table") else (st, b),
                      lambda m, p, q, st, b: (st, b["items"]) if p.endswith("/table") else (st, b),
                      lambda m, p, q, st, b: (st, dict(b, itemsTotal=b["itemsTotal"] + 1)) if p.endswith("/table") else (st, b)):
            meta = self.client(fault)
            self.assert_stops(meta.resolve_tables)

    def test_delete_requires_confirmed_absence(self):
        for status in (200, 204):
            fake = FakeMeta(synthetic_rows(), delete_status=status)
            meta = live.MetaClient("t", fake)
            meta.resolve_tables()
            meta.deletable_tables = {meta.table_ids["products"]}
            self.assertTrue(meta.delete("products", 1))
            self.assertEqual(fake.log[-2:], [("DELETE", f"/workspace/2/table/{TABLE_IDS['products']}/content/1"),
                                             ("GET", f"/workspace/2/table/{TABLE_IDS['products']}/content/1")])
        for kwargs in (dict(delete_status=202), dict(delete_status=500), dict(delete_status=404), dict(sticky={"products"})):
            fake = FakeMeta(synthetic_rows(), **kwargs)
            meta = live.MetaClient("t", fake)
            meta.resolve_tables()
            meta.deletable_tables = {meta.table_ids["products"]}
            self.assert_stops(lambda: meta.delete("products", 1))

    def test_single_record_reads_need_delete_permission(self):
        meta = live.MetaClient("t", FakeMeta(synthetic_rows()))
        meta.resolve_tables()
        self.assert_stops(lambda: meta._request("GET", f"/workspace/2/table/{TABLE_IDS['user']}/content/7"))

    def test_cleanup_stops_on_malformed_counts_without_deleting(self):
        fake = FakeMeta(synthetic_rows(), faults=self.content_fault(lambda b, q: b.pop("itemsTotal")))
        lines = []
        code = cleanup_live.run_cleanup(ENV, live.CLEANUP_PHRASE, execute=True, cli_runner=fake_cli(),
                                        meta=live.MetaClient("t", fake), transport=fake, out=lines.append)
        self.assertEqual(code, 2)
        self.assertFalse(any(m == "DELETE" for m, _ in fake.log))

    def test_live_runner_stops_on_malformed_counts(self):
        fake = FakeMeta({}, faults=self.content_fault(lambda b, q: b.update(itemsTotal="0")))
        calls = []
        code, _ = suite_module.run_suite(ENV, target="live-pmf", confirm_live=live.CONFIRM_PHRASE,
                                         transport=lambda *a: calls.append(a), cli_runner=fake_cli(),
                                         meta_client=live.MetaClient("t", fake), out=lambda *_: None)
        self.assertEqual((code, calls), (2, []))


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

    def test_reports_incomplete_when_a_delete_is_not_confirmed(self):
        meta = FakeMeta(synthetic_rows(), sticky={"products"})  # server claims success but the row remains
        code, lines = self.do_cleanup(meta, execute=True)
        self.assertEqual(code, 4)
        self.assertTrue(lines[-1].startswith("INCOMPLETE"))

    def test_stops_if_contents_change_after_verification(self):
        meta = FakeMeta(synthetic_rows())
        original = live.MetaClient.counts

        def counts(self_):
            result = original(self_)
            result["customers"] += 1
            return result

        live.MetaClient.counts = counts
        self.addCleanup(setattr, live.MetaClient, "counts", original)
        code, lines = self.do_cleanup(meta, execute=True)
        self.assertEqual(code, 2)
        self.assertFalse(any(m == "DELETE" for m, _ in meta.log))


class DeploymentChecks(unittest.TestCase):
    INV = check_dry_run.expected_inventory()

    def preview(self, workspace="2", host=live.LIVE_HOST, ws_name="pmf", verbs=True, extra=(), drop=0,
                summary=True, changes_header=True, mutate=None):
        lines = ["  CREATE           api_group          PMF App"]
        lines += [f"  CREATE           query              {v} {r}" if verbs else f"  CREATE           query              {r}"
                  for v, r in self.INV["query"]]
        lines += [f"  CREATE           function           {f}" for f in self.INV["function"]]
        lines = lines[:len(lines) - drop] + list(extra)
        if mutate:
            lines = mutate(lines)
        head = [f"=== Push Preview: workspace {workspace} ===", f"  instance: {host}  |  workspace: {ws_name}  |  cli: v1.3.4", ""]
        if summary:
            head += [f"  API Groups           +1 created", f"  Queries              +48 created", f"  Functions            +34 created", ""]
        return "\n".join(head + (["--- Changes ---", ""] if changes_header else []) + lines) + "\n"

    def status(self, text, cli_exit=0):
        return check_dry_run.check(text, self.INV, cli_exit)[0]

    def test_inventory_from_sources(self):
        self.assertEqual(check_dry_run.expected_objects(), {"api_group": 1, "query": 48, "function": 34})
        self.assertEqual(self.INV["api_group"], [("PMF App", "pmf-app")])

    def test_exact_preview_passes(self):
        self.assertEqual(self.status(self.preview()), 0)
        self.assertEqual(self.status(self.preview(summary=False)), 0)

    def test_verbless_preview_requires_human_review(self):
        status, problems, notes = check_dry_run.check(self.preview(verbs=False), self.INV, 0)
        self.assertEqual((status, problems), (3, []))
        self.assertTrue(notes)

    def test_negative_controls(self):
        q0 = self.INV["query"][0]
        fails = {
            "cli exit nonzero": (self.preview(), 1),
            "wrong workspace id": (self.preview(workspace="1"), 0),
            "wrong instance": (self.preview(host="other.xano.io"), 0),
            "wrong workspace name": (self.preview(ws_name="goodz"), 0),
            "missing header": (self.preview().replace("=== Push Preview: workspace 2 ===\n", ""), 0),
            "missing identity": ("\n".join(l for l in self.preview().splitlines() if "instance:" not in l), 0),
            "missing changes section": (self.preview(changes_header=False), 0),
            "empty output": ("", 0),
            "truncated output": (self.preview(drop=5), 0),
            "truncated output without summary": (self.preview(drop=5, summary=False), 0),
            "verbless truncated without summary": (self.preview(verbs=False, drop=40, summary=False), 0),
            "update op": (self.preview(extra=["  UPDATE           function           pmf/auth/require_owner"]), 0),
            "delete op": (self.preview(extra=["  DELETE           query              GET auth/me"]), 0),
            "table change": (self.preview(extra=["  CREATE           table              notes"]), 0),
            "auth endpoint": (self.preview(extra=["  CREATE           query              POST auth/signup"]), 0),
            "auth group": (self.preview(mutate=lambda ls: ["  CREATE           api_group          Authentication"] + ls[1:]), 0),
            "unknown type": (self.preview(extra=["  CREATE           middleware         pmf/x"]), 0),
            "renamed function": (self.preview(mutate=lambda ls: [l.replace("pmf/lock/wave", "pmf/lock/wav") for l in ls]), 0),
            "extra function": (self.preview(extra=["  CREATE           function           pmf/extra"]), 0),
            "wrong group": (self.preview(mutate=lambda ls: ["  CREATE           api_group          Other App"] + ls[1:]), 0),
            "duplicate group": (self.preview(extra=["  CREATE           api_group          PMF App"]), 0),
            "verb swapped": (self.preview(mutate=lambda ls: [l.replace(f"{q0[0]} {q0[1]}", f"PUT {q0[1]}", 1) for l in ls]), 0),
            "extra endpoint": (self.preview(extra=["  CREATE           query              GET admin/export"]), 0),
            "verbless missing route": (self.preview(verbs=False, drop=35), 0),
            "unparseable line": (self.preview(extra=["  something unexpected happened"]), 0),
            "push blocked": (self.preview(extra=[""]) + "Push blocked: 1 critical error(s) found.\n", 0),
            "summary mismatch": (self.preview().replace("+48 created", "+47 created"), 0),
            "summary non-create": (self.preview().replace("+34 created", "+33 created, ~1 updated"), 0),
        }
        for label, (text, code) in fails.items():
            with self.subTest(label):
                self.assertEqual(self.status(text, code), 1, label)

    def test_cli_requires_exit_status(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write(self.preview())
        argv = sys.argv
        try:
            sys.argv = ["check_dry_run.py", fh.name, "--cli-exit", "0"]
            self.assertEqual(check_dry_run.main(), 0)
            sys.argv = ["check_dry_run.py", fh.name, "--cli-exit", "2"]
            self.assertEqual(check_dry_run.main(), 1)
            sys.argv = ["check_dry_run.py", fh.name]
            with self.assertRaises(SystemExit):
                check_dry_run.main()
        finally:
            sys.argv = argv
            pathlib.Path(fh.name).unlink()

    def test_readback_comparator_on_exact_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            after, before = pathlib.Path(tmp, "after"), pathlib.Path(tmp, "before")
            for f in compare_readback.APP.rglob("*.xs"):
                target = after / f.relative_to(compare_readback.APP)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f.read_text())
            for d in (before, after):
                (d / "table").mkdir(parents=True, exist_ok=True)
                (d / "table" / "user.xs").write_text("table user {}\n")
            report = compare_readback.compare(after, before)
            self.assertEqual(report["structural_problems"], [])
            self.assertEqual(report["counts"]["equivalent"], 83)
            (after / "table" / "user.xs").write_text("table user { changed }\n")
            self.assertTrue(any("pre-existing document changed" in p for p in compare_readback.compare(after, before)["structural_problems"]))


class ReadbackClassification(unittest.TestCase):
    """Regression fixtures taken from the observed post-deployment read-back."""

    def cls(self, local, pulled, key=("function", "pmf/x")):
        return compare_readback.classify(key, local, pulled)

    def wrap(self, body, name='function "pmf/x"', guid=None):
        return f"{name} {{\n  stack {{\n{body}\n  }}\n" + (f'  guid = "{guid}"\n' if guid else "") + "}\n"

    def test_documented_formatting_is_equivalent(self):
        cases = [
            ('query "products" verb=GET {\n}\n', "query products verb=GET {\n}\n"),
            (self.wrap('    var $r {\n      value = {a: 1, b: 2}\n    }'), self.wrap("    var $r {\n      value = {\n        a: 1\n        b: 2\n      }\n    }")),
            (self.wrap('    db.query x {\n      join = {t: {table: "t", type: "inner", where: $db.x.id == $db.t.id}}\n    } as $q'),
             self.wrap('    db.query x {\n      join = {t: {table: "t", where: $db.x.id == $db.t.id}}\n    } as $q')),
            (self.wrap('    precondition ($a) {\n      error_type = "standard"\n      error = "X: y"\n    }'), self.wrap('    precondition ($a) {\n      error = "X: y"\n    }')),
            (self.wrap("    test \"t\" {\n      expect.to_throw\n    }"), self.wrap('    test "t" {\n      expect.to_throw {\n        exception = ""\n      }\n    }')),
            (self.wrap("    var $o {\n      value = {\n        eligible_count : ($rows|count)\n      }\n    }"), self.wrap("    var $o {\n      value = {\n        eligible_count: $rows|count\n      }\n    }")),
            (self.wrap('    var $o {\n      value = $c|set:"segment":($segment)\n    }'), self.wrap('    var $o {\n      value = $c|set:"segment":$segment\n    }')),
            (self.wrap("    var $o {\n      value = $items|push:($row)\n    }"), self.wrap("    var $o {\n      value = $items|push:$row\n    }")),
            (self.wrap("    // comment\n    var $o {\n      value = 1\n    }", guid="abc"), self.wrap("    var $o {\n      value = 1\n    }", guid="xyz")),
        ]
        for local, pulled in cases:
            with self.subTest(local=local[:40]):
                self.assertEqual(self.cls(local, pulled)[0], "EQUIVALENT")

    def test_api_group_attribute_order(self):
        a = 'api_group "PMF App" {\n  canonical = "pmf-app"\n  history = 0\n  tags = ["pmf"]\n}\n'
        b = 'api_group "PMF App" {\n  canonical = "pmf-app"\n  tags = ["pmf"]\n  history = 0\n}\n'
        self.assertEqual(compare_readback.classify(("api_group", "PMF App"), a, b)[0], "EQUIVALENT")
        c = b.replace("history = 0", "history = 100")
        self.assertEqual(compare_readback.classify(("api_group", "PMF App"), a, c)[0], "UNEXPLAINED")

    def assert_runtime(self, local, pulled, expected_class):
        status, items = self.cls(local, pulled)
        self.assertEqual(status, "RUNTIME")
        self.assertIn(expected_class, [c for c, _ in items])

    def test_known_uncertainties_are_runtime_not_equivalent(self):
        self.assert_runtime(self.wrap("  input {\n    bool unsegmented?=false\n  }"), self.wrap("  input {\n    bool unsegmented?\n  }"), "missing_default")
        self.assert_runtime(self.wrap('    var $s {\n      value = {a: $d|get:"a"}\n    }'), self.wrap('    var $s {\n      value = `{a: $d|get:"a"}`\n    }'), "expression_mode")
        self.assert_runtime(self.wrap("    test \"t\" {\n      input = {\n        rows: [\n          {a: 1}\n        ]\n      }\n    }"),
                            self.wrap("    test \"t\" {\n      input = {\n        rows: ```\n          [\n            {a: 1}\n          ]\n          ```\n      }\n    }"), "test_expression_block")
        self.assert_runtime(self.wrap("    var $i {\n      value = $f|slice:$o:($o + $p)\n    }"), self.wrap("    var $i {\n      value = $f\n        |slice:$o:$o + $p\n    }"), "grouping")
        self.assert_runtime(self.wrap('    precondition ($x != null && (["a", "b"]|some:$$ == $x)) {\n      error = "E: e"\n    }'),
                            self.wrap('    precondition ($x != null && ["a", "b"]|some:$$ == $x) {\n      error = "E: e"\n    }'), "grouping")
        self.assert_runtime(self.wrap('    var.update $items {\n      value = $items|push:($s|set:"c":$n)\n    }'), self.wrap('    var.update $items {\n      value = $items|push:$s|set:"c":$n\n    }'), "grouping")

    def test_real_changes_are_unexplained(self):
        base = self.wrap('    var $v {\n      value = $rows|filter:$$.level == "very"\n    }\n    precondition ($a > 0) {\n      error = "E: e"\n    }')
        changed = [
            base.replace('"very"', '"somewhat"'),
            base.replace("$a > 0", "$a >= 0"),
            base.replace('    precondition ($a > 0) {\n      error = "E: e"\n    }', ""),
            base.replace("$$.level", "$$.status"),
        ]
        for pulled in changed:
            self.assertEqual(self.cls(base, pulled)[0], "UNEXPLAINED")
        self.assertEqual(self.cls(self.wrap("  input {\n    bool u?=false\n  }"), self.wrap("  input {\n    bool u?=true\n  }"))[0], "UNEXPLAINED")

    def test_structural_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            after = pathlib.Path(tmp, "after")
            for f in compare_readback.APP.rglob("*.xs"):
                target = after / f.relative_to(compare_readback.APP)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f.read_text())
            fn = next(after.rglob("require_owner.xs"))
            fn.write_text(re.sub(r'guid = "[^"]+"', 'guid = "different"', fn.read_text()))
            extra = after / "function" / "pmf" / "extra.xs"
            extra.write_text('function "pmf/extra" {\n}\n')
            problems = compare_readback.compare(after)["structural_problems"]
            self.assertTrue(any("guid mismatch" in p for p in problems))
            self.assertTrue(any("unexpected PMF object" in p for p in problems))
            next(after.rglob("products_GET.xs")).unlink()
            self.assertTrue(any("missing in Xano" in p for p in compare_readback.compare(after)["structural_problems"]))


if __name__ == "__main__":
    unittest.main()
