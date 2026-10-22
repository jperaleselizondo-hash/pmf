#!/usr/bin/env python3
"""PMF Engine API V1 — HTTP test suite (synthetic data, isolated environment ONLY).

Implements the test matrix of docs/API_V1_PROPOSAL.md §6 / Appendix R8.5. Standard library only.

Required environment (never commit values):
  PMF_TEST_BASE_URL        https://<isolated-host>/api:pmf-app
  PMF_TEST_AUTH_URL        https://<isolated-host>/api:<authentication canonical in the isolated env>
  PMF_TEST_ENV_HOST        <isolated-host> as reported by `xano ephemeral get` (operator-recorded)
  PMF_TEST_TENANT_NAME     isolated tenant name
  PMF_TEST_OWNER_TOKEN     token of the synthetic designated owner (email @pmf-test.invalid)
  PMF_TEST_INTRUDER_TOKEN  token of a second synthetic user (email @pmf-test.invalid)

Usage:
  python3 tests/api/pmf_api_tests.py --confirm-tenant <name> [--skip-concurrency] [--only W01,P01]

The run aborts before its first write unless the configuration and the read-only canary prove an
isolated, synthetic-only environment. Manual checks (S03, S08, S09) are listed at the end.
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pmf_reference as ref  # noqa: E402
from safety import UnsafeEnvironment, check_canary, check_config  # noqa: E402

DAY = 86_400_000
MISSING_ID = 999_999_999
ROUTES = [
    ("GET", "products"), ("POST", "products"),
    ("GET", "products/{id}"), ("PATCH", "products/{id}"),
    ("GET", "products/{id}/segments"), ("POST", "products/{id}/segments"),
    ("PATCH", "segments/{id}"), ("DELETE", "segments/{id}"),
    ("GET", "products/{id}/customers"), ("POST", "products/{id}/customers"),
    ("GET", "customers/{id}"), ("PATCH", "customers/{id}"), ("DELETE", "customers/{id}"),
    ("GET", "customers/{id}/interviews"), ("POST", "customers/{id}/interviews"),
    ("GET", "interviews/{id}"), ("PATCH", "interviews/{id}"), ("DELETE", "interviews/{id}"),
    ("GET", "products/{id}/survey-waves"), ("POST", "products/{id}/survey-waves"),
    ("GET", "survey-waves/{id}"), ("PATCH", "survey-waves/{id}"), ("DELETE", "survey-waves/{id}"),
    ("POST", "survey-waves/{id}/status"),
    ("GET", "survey-waves/{id}/participations"), ("POST", "survey-waves/{id}/participations"),
    ("PATCH", "participations/{id}"), ("DELETE", "participations/{id}"),
    ("GET", "survey-waves/{id}/report"),
    ("GET", "products/{id}/insights"), ("POST", "products/{id}/insights"),
    ("GET", "insights/{id}"), ("PATCH", "insights/{id}"), ("DELETE", "insights/{id}"),
    ("POST", "insights/{id}/review-status"), ("POST", "insights/{id}/evidence"),
    ("PATCH", "evidence/{id}"), ("DELETE", "evidence/{id}"),
    ("GET", "products/{id}/hypotheses"), ("POST", "insights/{id}/hypotheses"),
    ("GET", "hypotheses/{id}"), ("PATCH", "hypotheses/{id}"), ("DELETE", "hypotheses/{id}"),
    ("POST", "hypotheses/{id}/experiments"),
    ("PATCH", "experiments/{id}"), ("DELETE", "experiments/{id}"),
    ("GET", "products/{id}/overview"), ("GET", "products/{id}/lookups"),
]
assert len(ROUTES) == 48
SAMPLE_BODIES = {
    ("POST", "products"): {"name": "SYNTH-sweep"},
    ("POST", "products/{id}/segments"): {"name": "sweep"},
    ("POST", "products/{id}/customers"): {},
    ("POST", "customers/{id}/interviews"): {"conducted_at": 0},
    ("POST", "products/{id}/survey-waves"): {"name": "sweep", "eligibility_rule": "r", "questionnaire_version": "v"},
    ("POST", "survey-waves/{id}/status"): {"action": "close"},
    ("POST", "survey-waves/{id}/participations"): {"customer_ids": [MISSING_ID]},
    ("POST", "products/{id}/insights"): {"type": "problem", "statement": "sweep"},
    ("POST", "insights/{id}/review-status"): {"review_status": "reviewed"},
    ("POST", "insights/{id}/evidence"): {"excerpt": "sweep", "relationship": "supports"},
    ("POST", "insights/{id}/hypotheses"): {"statement": "s", "expected_outcome": "o", "success_metric": "m"},
    ("POST", "hypotheses/{id}/experiments"): {"name": "n", "method": "m"},
}


class Response:
    def __init__(self, status, body):
        self.status = status
        self.body = body

    @property
    def code(self):
        message = (self.body or {}).get("message", "") if isinstance(self.body, dict) else ""
        return message.split(":", 1)[0] if ":" in message else message

    def __repr__(self):
        return f"<{self.status} {json.dumps(self.body)[:300]}>"


class Api:
    """Minimal JSON client. Records every response body for leakage checks (S06/S07)."""

    def __init__(self, base, token, recorder):
        self.base = base.rstrip("/")
        self.token = token
        self.recorder = recorder

    def call(self, method, path, body=None, params=None):
        url = f"{self.base}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        data = json.dumps(body).encode() if body is not None and method != "GET" else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                status, raw = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
        try:
            parsed = json.loads(raw.decode() or "null")
        except ValueError:
            parsed = {"raw": raw.decode(errors="replace")[:500]}
        self.recorder.append(parsed)
        return Response(status, parsed)


class Failure(AssertionError):
    pass


def expect(cond, msg):
    if not cond:
        raise Failure(msg)


def ok(r, status=200):
    expect(r.status == status, f"expected {status}, got {r!r}")
    return r.body


def rejected(r, status=400, code=None):
    expect(r.status == status, f"expected {status}{' ' + code if code else ''}, got {r!r}")
    if code:
        expect(r.code == code, f"expected error code {code}, got {r.code!r}")


def close(a, b, tol=1e-9):
    return a is not None and b is not None and abs(a - b) <= tol


class Suite:
    def __init__(self, base, auth_base, owner_token, intruder_token, tag):
        self.recorded = []
        self.owner = Api(base, owner_token, self.recorded)
        self.intruder = Api(base, intruder_token, self.recorded)
        self.anon = Api(base, None, self.recorded)
        self.owner_auth = Api(auth_base, owner_token, self.recorded)
        self.intruder_auth = Api(auth_base, intruder_token, self.recorded)
        self.tag = tag
        self.marker = f"SENSITIVE-MARKER-{tag}"
        self.fx = {}
        self.results = []
        self.now = int(time.time() * 1000)

    # ---------- helpers ----------
    def product(self, name):
        return ok(self.owner.call("POST", "products", {"name": f"SYNTH-{self.tag}-{name}"}))

    def segment(self, pid, name):
        return ok(self.owner.call("POST", f"products/{pid}/segments", {"name": name}))

    def customer(self, pid, label, segment_id=None, **extra):
        body = {"name": f"SYNTH {label}", "email": f"{label.lower()}-{self.tag}@pmf-test.invalid", "lifecycle_stage": "active"}
        if segment_id:
            body["segment_id"] = segment_id
        body.update(extra)
        return ok(self.owner.call("POST", f"products/{pid}/customers", body))

    def wave(self, pid, name, version, started_days_ago=10, rule="Active synthetic users for 2+ weeks"):
        return ok(self.owner.call("POST", f"products/{pid}/survey-waves", {
            "name": name, "eligibility_rule": rule, "questionnaire_version": version,
            "started_at": self.now - started_days_ago * DAY}))

    def add(self, wid, customer_ids):
        created = ok(self.owner.call("POST", f"survey-waves/{wid}/participations", {"customer_ids": customer_ids}))["created"]
        return {p["customer_id"]: p for p in created}

    def respond(self, participation_id, level, days_ago=8, invited_days_ago=None, **answers):
        body = {"responded_at": self.now - days_ago * DAY}
        if level:
            body["disappointment_level"] = level
        if invited_days_ago is not None:
            body["invited_at"] = self.now - invited_days_ago * DAY
        body.update(answers)
        return ok(self.owner.call("PATCH", f"participations/{participation_id}", body))

    def report(self, wid, **params):
        return ok(self.owner.call("GET", f"survey-waves/{wid}/report", params=params or None))

    # ---------- fixture (docs/API_V1_PROPOSAL.md §6.1) ----------
    def build_fixture(self):
        fx = self.fx
        fx["A"], fx["B"] = self.product("A"), self.product("B")
        a, b = fx["A"]["id"], fx["B"]["id"]
        fx["A1"], fx["A2"] = self.segment(a, "Solo founders"), self.segment(a, "Agencies")
        fx["B1"] = self.segment(b, "B segment")
        for label, seg in (("C1", "A1"), ("C2", "A1"), ("C3", "A2"), ("C4", "A2"), ("C5", None), ("C6", "A1"), ("C7", "A2")):
            fx[label] = self.customer(a, label, fx[seg]["id"] if seg else None)
        fx["CB1"] = self.customer(b, "CB1", fx["B1"]["id"])
        fx["I1"] = ok(self.owner.call("POST", f"customers/{fx['C1']['id']}/interviews", {
            "conducted_at": self.now - 20 * DAY, "notes": "  Reconciling invoices takes two hours every Friday.  ",
            "problem_context": "Missed a payment run last month."}))
        fx["I2"] = ok(self.owner.call("POST", f"customers/{fx['C3']['id']}/interviews", {
            "conducted_at": self.now - 19 * DAY, "notes": "Uses spreadsheets; would not pay yet."}))
        fx["IB1"] = ok(self.owner.call("POST", f"customers/{fx['CB1']['id']}/interviews", {
            "conducted_at": self.now - 18 * DAY, "notes": "Other product interview."}))
        fx["W1"] = self.wave(a, "W1", "v1")
        p = self.add(fx["W1"]["id"], [fx[c]["id"] for c in ("C1", "C2", "C3", "C4", "C5")])
        fx["P"] = {c: p[fx[c]["id"]] for c in ("C1", "C2", "C3", "C4", "C5")}
        for c in ("C3", "C4"):
            ok(self.owner.call("PATCH", f"participations/{fx['P'][c]['id']}", {"invited_at": self.now - 9 * DAY}))
        self.respond(fx["P"]["C1"]["id"], "very", invited_days_ago=9, main_benefit="Saves the Friday reconciliation")
        self.respond(fx["P"]["C2"]["id"], "somewhat", invited_days_ago=9, main_benefit="Fewer spreadsheet errors")
        self.respond(fx["P"]["C5"]["id"], "not", improvement_request="Needs bank import")
        fx["W2"] = self.wave(a, "W2", "v2", started_days_ago=5)
        p2 = self.add(fx["W2"]["id"], [fx[c]["id"] for c in ("C1", "C6", "C7")])
        fx["P2"] = {c: p2[fx[c]["id"]] for c in ("C1", "C6", "C7")}
        self.respond(fx["P2"]["C1"]["id"], "very", days_ago=4)
        self.respond(fx["P2"]["C6"]["id"], "somewhat", days_ago=4)
        fx["W3"] = self.wave(a, "W3", "v2", started_days_ago=2)
        fx["P3"] = self.add(fx["W3"]["id"], [fx["C6"]["id"]])

    # ---------- runner ----------
    def run(self, tests, only=None):
        for tid, desc, fn in tests:
            if only and tid not in only:
                continue
            try:
                fn(self)
                self.results.append((tid, "PASS", desc, ""))
            except Failure as exc:
                self.results.append((tid, "FAIL", desc, str(exc)))
            except Exception as exc:  # noqa: BLE001 - report unexpected errors per test
                self.results.append((tid, "ERROR", desc, f"{type(exc).__name__}: {exc}"))


TESTS = []


def case(tid, desc):
    def register(fn):
        TESTS.append((tid, desc, fn))
        return fn
    return register


# ---------------- Security ----------------
def sweep(api, expected, label):
    bad = []
    for verb, route in ROUTES:
        body = SAMPLE_BODIES.get((verb, route), {}) if verb in ("POST", "PATCH") else None
        r = api.call(verb, route.replace("{id}", str(MISSING_ID)), body)
        if r.status != expected:
            bad.append(f"{verb} {route} -> {r.status}")
    expect(not bad, f"{label}: {bad}")


@case("S01", "every endpoint rejects requests without a token (401)")
def s01(s):
    sweep(s.anon, 401, "no token")


@case("S02", "every endpoint rejects a non-owner authenticated user (403)")
def s02(s):
    sweep(s.intruder, 403, "intruder")


@case("S04", "missing or foreign ids return 404 for the owner")
def s04(s):
    for path in ("products/{0}", "customers/{0}", "interviews/{0}", "survey-waves/{0}", "insights/{0}", "hypotheses/{0}"):
        rejected(s.owner.call("GET", path.format(MISSING_ID)), 404, "NOT_FOUND")


@case("S05", "server-controlled fields cannot be mass-assigned")
def s05(s):
    me = ok(s.owner_auth.call("GET", "auth/me"))
    r = s.owner.call("POST", "products", {"name": f"SYNTH-{s.tag}-MASS", "owner_user_id": me["id"] + 1000})
    expect(r.status == 400 or (r.status == 200 and r.body["owner_user_id"] == me["id"]), f"owner_user_id assigned: {r!r}")
    r = s.owner.call("POST", f"products/{s.fx['A']['id']}/insights", {"type": "problem", "statement": "x", "review_status": "reviewed"})
    expect(r.status == 400 or (r.status == 200 and r.body["review_status"] == "draft"), f"review_status assigned: {r!r}")
    if r.status == 200:
        ok(s.owner.call("DELETE", f"insights/{r.body['id']}"))
    w = s.owner.call("POST", f"products/{s.fx['A']['id']}/survey-waves", {"name": "MASS", "eligibility_rule": "r", "questionnaire_version": "v", "closed_at": s.now})
    expect(w.status == 400 or (w.status == 200 and w.body["closed_at"] is None), f"closed_at assigned: {w!r}")
    if w.status == 200:
        p = s.owner.call("POST", f"survey-waves/{w.body['id']}/participations", {"customer_ids": [s.fx["C7"]["id"]], "segment_id_snapshot": s.fx["A1"]["id"]})
        expect(p.status == 400 or p.body["created"][0]["segment_id_snapshot"] == s.fx["A2"]["id"], f"snapshot assigned: {p!r}")


@case("S06", "no response contains password fields or auth tokens")
def s06(s):
    blob = json.dumps(s.recorded)
    expect('"password"' not in blob, "a response contains a password field")
    expect('"authToken"' not in blob, "a response contains an auth token")


@case("S07", "error messages never echo sensitive input text")
def s07(s):
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {
        "interview_id": s.fx["I1"]["id"], "survey_participation_id": s.fx["P"]["C1"]["id"],
        "excerpt": s.marker, "relationship": "supports"}), 400, "EVIDENCE_SOURCE_XOR")
    rejected(s.owner.call("POST", f"customers/{s.fx['C1']['id']}/interviews", {
        "conducted_at": s.now + 2 * DAY, "notes": s.marker}), 400, "INVALID_TIMESTAMP")
    errors = [b for b in s.recorded if isinstance(b, dict) and "message" in b]
    expect(not any(s.marker in json.dumps(b) for b in errors), "sensitive marker echoed in an error")


# ---------------- Market ----------------
@case("M01", "created product belongs to the owner")
def m01(s):
    me = ok(s.owner_auth.call("GET", "auth/me"))
    expect(s.fx["A"]["owner_user_id"] == me["id"], "owner_user_id mismatch")
    names = [p["name"] for p in ok(s.owner.call("GET", "products", params={"per_page": 100}))["items"]]
    expect(s.fx["A"]["name"] in names, "product not listed")


@case("M02", "segment names unique per product, reusable across products")
def m02(s):
    rejected(s.owner.call("POST", f"products/{s.fx['A']['id']}/segments", {"name": "Solo founders"}), 400, "DUPLICATE_SEGMENT_NAME")
    seg = ok(s.owner.call("POST", f"products/{s.fx['B']['id']}/segments", {"name": "Solo founders"}))
    ok(s.owner.call("DELETE", f"segments/{seg['id']}"))


@case("M03", "a customer cannot use another product's segment")
def m03(s):
    rejected(s.owner.call("POST", f"products/{s.fx['A']['id']}/customers", {"name": "X", "segment_id": s.fx["B1"]["id"]}), 400, "CROSS_PRODUCT_REFERENCE")
    rejected(s.owner.call("PATCH", f"customers/{s.fx['C1']['id']}", {"segment_id": s.fx["B1"]["id"]}), 400, "CROSS_PRODUCT_REFERENCE")


@case("M04", "blank external_id is stored as null and never collides")
def m04(s):
    x = ok(s.owner.call("POST", f"products/{s.fx['A']['id']}/customers", {"name": "SYNTH blank1", "external_id": "  "}))
    y = ok(s.owner.call("POST", f"products/{s.fx['A']['id']}/customers", {"name": "SYNTH blank2", "external_id": ""}))
    expect(x["external_id"] is None and y["external_id"] is None, "blank external_id not normalized")
    for c in (x, y):
        ok(s.owner.call("DELETE", f"customers/{c['id']}"))


@case("M05", "external_id unique within a product only")
def m05(s):
    ext = f"ext-{s.tag}"
    a = ok(s.owner.call("POST", f"products/{s.fx['A']['id']}/customers", {"name": "SYNTH ext", "external_id": ext}))
    rejected(s.owner.call("POST", f"products/{s.fx['A']['id']}/customers", {"name": "SYNTH ext2", "external_id": ext}), 400, "DUPLICATE_EXTERNAL_ID")
    b = ok(s.owner.call("POST", f"products/{s.fx['B']['id']}/customers", {"name": "SYNTH ext3", "external_id": ext}))
    for c in (a, b):
        ok(s.owner.call("DELETE", f"customers/{c['id']}"))


@case("M06", "a prospect can be created without email or account")
def m06(s):
    c = ok(s.owner.call("POST", f"products/{s.fx['A']['id']}/customers", {}))
    expect(c["lifecycle_stage"] == "prospect" and c["email"] is None, f"unexpected prospect {c}")
    ok(s.owner.call("DELETE", f"customers/{c['id']}"))


@case("M07", "a customer's product cannot be changed")
def m07(s):
    r = s.owner.call("PATCH", f"customers/{s.fx['C7']['id']}", {"product_id": s.fx["B"]["id"]})
    expect(r.status == 400 or (r.status == 200 and r.body["product_id"] == s.fx["A"]["id"]), f"product_id changed: {r!r}")


# ---------------- Research ----------------
@case("R01", "raw interview notes are stored verbatim (untrimmed)")
def r01(s):
    i = ok(s.owner.call("GET", f"interviews/{s.fx['I1']['id']}"))
    expect(i["notes"] == "  Reconciling invoices takes two hours every Friday.  ", "notes altered")
    listing = ok(s.owner.call("GET", f"customers/{s.fx['C1']['id']}/interviews"))
    expect("notes" not in listing["items"][0] and listing["items"][0]["has_notes"], "list leaks raw text")


@case("R02", "cited interview text is locked; uncited text editable")
def r02(s):
    rejected(s.owner.call("PATCH", f"interviews/{s.fx['I1']['id']}", {"notes": "rewritten"}), 400, "CITED_CONTENT_LOCKED")
    ok(s.owner.call("PATCH", f"interviews/{s.fx['I1']['id']}", {"conducted_at": s.now - 21 * DAY}))
    ok(s.owner.call("PATCH", f"interviews/{s.fx['I2']['id']}", {"existing_alternatives": "Spreadsheets"}))


@case("R03", "referenced customers and cited interviews cannot be deleted")
def r03(s):
    rejected(s.owner.call("DELETE", f"customers/{s.fx['C1']['id']}"), 400, "IN_USE")
    rejected(s.owner.call("DELETE", f"interviews/{s.fx['I1']['id']}"), 400, "IN_USE")
    rejected(s.owner.call("DELETE", f"segments/{s.fx['A1']['id']}"), 400, "IN_USE")


@case("R04", "interview timestamps: future beyond 5 minutes rejected, historical allowed")
def r04(s):
    rejected(s.owner.call("POST", f"customers/{s.fx['C2']['id']}/interviews", {"conducted_at": s.now + 3_600_000}), 400, "INVALID_TIMESTAMP")
    i = ok(s.owner.call("POST", f"customers/{s.fx['C2']['id']}/interviews", {"conducted_at": s.now - 400 * DAY, "notes": "Historical"}))
    ok(s.owner.call("DELETE", f"interviews/{i['id']}"))


# ---------------- Surveys ----------------
@case("W01", "participations snapshot the customer's segment at eligibility")
def w01(s):
    p = s.fx["P"]
    expect(p["C1"]["segment_id_snapshot"] == s.fx["A1"]["id"], "C1 snapshot")
    expect(p["C3"]["segment_id_snapshot"] == s.fx["A2"]["id"], "C3 snapshot")
    expect(p["C5"]["segment_id_snapshot"] is None, "C5 snapshot")


@case("W02", "duplicate participation is rejected")
def w02(s):
    rejected(s.owner.call("POST", f"survey-waves/{s.fx['W1']['id']}/participations", {"customer_ids": [s.fx["C1"]["id"]]}), 400, "DUPLICATE_PARTICIPATION")


@case("W03", "bulk add is all-or-nothing (duplicates in body, cross-product customer)")
def w03(s):
    wid = s.fx["W3"]["id"]
    rejected(s.owner.call("POST", f"survey-waves/{wid}/participations", {"customer_ids": [s.fx["C7"]["id"], s.fx["C7"]["id"]]}), 400, "DUPLICATE_IN_REQUEST")
    rejected(s.owner.call("POST", f"survey-waves/{wid}/participations", {"customer_ids": [s.fx["C7"]["id"], s.fx["CB1"]["id"]]}), 400, "CROSS_PRODUCT_REFERENCE")
    items = ok(s.owner.call("GET", f"survey-waves/{wid}/participations", params={"per_page": 100}))["items"]
    expect(all(i["customer"]["id"] != s.fx["C7"]["id"] for i in items), "partial insert happened")


@case("W04", "a category without responded_at is rejected")
def w04(s):
    rejected(s.owner.call("PATCH", f"participations/{s.fx['P3'][s.fx['C6']['id']]['id']}", {"disappointment_level": "very"}), 400, "RESPONSE_STATE")


@case("W05", "responded_at without category is an incomplete response")
def w05(s):
    pid = s.fx["P3"][s.fx["C6"]["id"]]["id"]
    r = ok(s.owner.call("PATCH", f"participations/{pid}", {"responded_at": s.now - DAY}))
    expect(r["status"] == "incomplete", f"status {r['status']}")
    rep = s.report(s.fx["W3"]["id"])
    expect(rep["selected"]["incomplete_response_count"] == 1 and rep["selected"]["valid_response_count"] == 0, "incomplete counted")
    ok(s.owner.call("PATCH", f"participations/{pid}", {"clear": ["responded_at"]}))


@case("W06", "responses require a started wave and responded_at >= started_at")
def w06(s):
    draft = ok(s.owner.call("POST", f"products/{s.fx['A']['id']}/survey-waves", {"name": "Draft", "eligibility_rule": "r", "questionnaire_version": "v9"}))
    p = s.add(draft["id"], [s.fx["C7"]["id"]])[s.fx["C7"]["id"]]
    rejected(s.owner.call("PATCH", f"participations/{p['id']}", {"responded_at": s.now - DAY, "disappointment_level": "not"}), 400, "WAVE_NOT_STARTED")
    ok(s.owner.call("PATCH", f"survey-waves/{draft['id']}", {"started_at": s.now - 2 * DAY}))
    rejected(s.owner.call("PATCH", f"participations/{p['id']}", {"responded_at": s.now - 3 * DAY, "disappointment_level": "not"}), 400, "INVALID_TIMESTAMP")
    rejected(s.owner.call("PATCH", f"participations/{p['id']}", {"responded_at": s.now + DAY, "disappointment_level": "not"}), 400, "INVALID_TIMESTAMP")
    ok(s.owner.call("DELETE", f"participations/{p['id']}"))
    ok(s.owner.call("DELETE", f"survey-waves/{draft['id']}"))


@case("W07", "eligibility rule and questionnaire version are frozen once participants exist")
def w07(s):
    rejected(s.owner.call("PATCH", f"survey-waves/{s.fx['W2']['id']}", {"questionnaire_version": "v2b"}), 400, "DEFINITION_LOCKED")
    rejected(s.owner.call("PATCH", f"survey-waves/{s.fx['W2']['id']}", {"eligibility_rule": "changed"}), 400, "DEFINITION_LOCKED")
    empty = ok(s.owner.call("POST", f"products/{s.fx['A']['id']}/survey-waves", {"name": "Empty", "eligibility_rule": "r", "questionnaire_version": "v1"}))
    ok(s.owner.call("PATCH", f"survey-waves/{empty['id']}", {"questionnaire_version": "v1.1"}))
    ok(s.owner.call("DELETE", f"survey-waves/{empty['id']}"))


@case("W08", "a closed wave rejects participant, response, deletion and definition changes")
def w08(s):
    wid = s.fx["W1"]["id"]
    rejected(s.owner.call("POST", f"survey-waves/{wid}/status", {"action": "close", "closed_at": s.now - 30 * DAY}), 400, "INVALID_TIMESTAMP")
    closed = ok(s.owner.call("POST", f"survey-waves/{wid}/status", {"action": "close"}))
    expect(closed["state"] == "closed", "not closed")
    rejected(s.owner.call("POST", f"survey-waves/{wid}/participations", {"customer_ids": [s.fx["C6"]["id"]]}), 400, "WAVE_CLOSED")
    rejected(s.owner.call("PATCH", f"participations/{s.fx['P']['C3']['id']}", {"responded_at": s.now - DAY, "disappointment_level": "not"}), 400, "WAVE_CLOSED")
    rejected(s.owner.call("DELETE", f"participations/{s.fx['P']['C4']['id']}"), 400, "WAVE_CLOSED")
    rejected(s.owner.call("PATCH", f"survey-waves/{wid}", {"name": "renamed"}), 400, "WAVE_CLOSED")
    rejected(s.owner.call("POST", f"survey-waves/{wid}/status", {"action": "close"}), 400, "WAVE_ALREADY_CLOSED")


@case("W09", "explicit reopen allows corrections; close again")
def w09(s):
    wid = s.fx["W1"]["id"]
    expect(ok(s.owner.call("POST", f"survey-waves/{wid}/status", {"action": "reopen"}))["state"] == "open", "not reopened")
    ok(s.owner.call("PATCH", f"survey-waves/{wid}", {"name": "W1"}))
    ok(s.owner.call("POST", f"survey-waves/{wid}/status", {"action": "close"}))


@case("W10", "moving a customer to another segment leaves historical reports unchanged")
def w10(s):
    before = s.report(s.fx["W1"]["id"], segment_id=s.fx["A1"]["id"])["selected"]
    ok(s.owner.call("PATCH", f"customers/{s.fx['C2']['id']}", {"segment_id": s.fx["A2"]["id"]}))
    after = s.report(s.fx["W1"]["id"], segment_id=s.fx["A1"]["id"])["selected"]
    expect(before["valid_response_count"] == after["valid_response_count"] == 2, "segment report changed")
    expect(close(after["pmf_percent"], 50.0), f"A1 pmf {after['pmf_percent']}")
    ok(s.owner.call("PATCH", f"customers/{s.fx['C2']['id']}", {"segment_id": s.fx["A1"]["id"]}))


@case("W11", "a wave with participants cannot be deleted")
def w11(s):
    rejected(s.owner.call("DELETE", f"survey-waves/{s.fx['W1']['id']}"), 400, "IN_USE")


# ---------------- Numerical / cohort ----------------
@case("P01", "fixture W1 overall: 5/4/3, 1 very, PMF 33.333...% (no truncation)")
def p01(s):
    sel = s.report(s.fx["W1"]["id"])["selected"]
    expected = ref.count_rows(ref.W1_ROWS)
    for key in ("eligible_count", "invited_count", "valid_response_count", "incomplete_response_count", "invited_valid_count", "manual_valid_count"):
        expect(sel[key] == expected[key], f"{key}: {sel[key]} != {expected[key]}")
    expect(sel["counts"] == {"very": 1, "somewhat": 1, "not": 1}, f"counts {sel['counts']}")
    expect(close(sel["pmf_percent"], 100 / 3), f"pmf {sel['pmf_percent']}")


@case("P02", "segment results use snapshots: A1 50.0, A2 null, unsegmented 0.0")
def p02(s):
    wid = s.fx["W1"]["id"]
    expect(close(s.report(wid, segment_id=s.fx["A1"]["id"])["selected"]["pmf_percent"], 50.0), "A1")
    expect(s.report(wid, segment_id=s.fx["A2"]["id"])["selected"]["pmf_percent"] is None, "A2 must be null")
    expect(s.report(wid, unsegmented="true")["selected"]["pmf_percent"] == 0, "unsegmented must be 0.0, not null")
    by = {(b["segment"] or {}).get("id"): b["result"]["pmf_percent"] for b in s.report(wid)["by_segment"]}
    expect(close(by[s.fx["A1"]["id"]], 50.0) and by[s.fx["A2"]["id"]] is None and by[None] == 0, f"by_segment {by}")


@case("P03", "zero valid responses -> pmf null and NO_VALID_RESPONSES")
def p03(s):
    rep = s.report(s.fx["W3"]["id"])
    expect(rep["selected"]["pmf_percent"] is None and rep["selected"]["valid_response_count"] == 0, "pmf not null")
    expect(any(w["code"] == "NO_VALID_RESPONSES" for w in rep["warnings"]), "warning missing")


@case("P04", "invited response rate excludes manual responses")
def p04(s):
    sel = s.report(s.fx["W1"]["id"])["selected"]
    expect(sel["invited_response_rate"] == 0.5 and sel["manual_valid_count"] == 1, f"rate {sel['invited_response_rate']}")
    expect(sel["response_rate_denominator"] == "invited_count", "denominator label")


@case("P05", "2 very of 3 valid -> 66.666...%")
def p05(s):
    w = s.wave(s.fx["A"]["id"], "P05", "v1", started_days_ago=3)
    ids = [s.fx[c]["id"] for c in ("C2", "C3", "C4")]
    parts = s.add(w["id"], ids)
    for cid, level in zip(ids, ("very", "very", "somewhat")):
        s.respond(parts[cid]["id"], level, days_ago=1)
    expect(close(s.report(w["id"])["selected"]["pmf_percent"], 200 / 3), "pmf 66.666")
    s.fx["W_P05"] = w


@case("P07", "repeat respondents and definition changes are flagged; first-time block excludes them")
def p07(s):
    rep = s.report(s.fx["W2"]["id"])
    codes = {w["code"] for w in rep["warnings"]}
    expect({"REPEAT_RESPONDENTS", "DEFINITION_CHANGED"} <= codes, f"warnings {codes}")
    expect(rep["first_time_only"]["excluded_repeat_respondents"] == 1, "C1 not excluded")
    expect(rep["first_time_only"]["result"]["valid_response_count"] == 1, "first-time valid count")
    expect(rep["comparable_with_previous"] is False, "comparability flag")


@case("P08", "open waves are flagged provisional; small samples flagged informational (<30)")
def p08(s):
    codes = {w["code"] for w in s.report(s.fx["W2"]["id"])["warnings"]}
    expect("WAVE_OPEN" in codes and "SMALL_SAMPLE" in codes, f"warnings {codes}")


@case("P09", "overview lists per-wave summaries without fabricated trends")
def p09(s):
    ov = ok(s.owner.call("GET", f"products/{s.fx['A']['id']}/overview"))
    names = [w["wave"]["name"] for w in ov["waves"]]
    expect({"W1", "W2", "W3"} <= set(names), f"waves {names}")
    expect(ov["customers"]["total"] >= 7, "customer total")


# ---------------- Evidence & insights ----------------
@case("E00", "create draft insight for evidence tests")
def e00(s):
    s.fx["INS"] = ok(s.owner.call("POST", f"products/{s.fx['A']['id']}/insights", {"type": "problem", "statement": "Reconciliation is a weekly pain", "segment_id": s.fx["A1"]["id"]}))
    expect(s.fx["INS"]["review_status"] == "draft" and s.fx["INS"]["confidence"] == "low", "defaults")


@case("I01", "an insight without evidence cannot be reviewed")
def i01(s):
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/review-status", {"review_status": "reviewed"}), 400, "EVIDENCE_REQUIRED")


@case("E01", "evidence with both sources is rejected")
def e01(s):
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"interview_id": s.fx["I1"]["id"], "survey_participation_id": s.fx["P"]["C1"]["id"], "excerpt": "x", "relationship": "supports"}), 400, "EVIDENCE_SOURCE_XOR")


@case("E02", "evidence with no source is rejected")
def e02(s):
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"excerpt": "x", "relationship": "supports"}), 400, "EVIDENCE_SOURCE_XOR")


@case("E03", "evidence from another product is rejected")
def e03(s):
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"interview_id": s.fx["IB1"]["id"], "excerpt": "x", "relationship": "supports"}), 400, "CROSS_PRODUCT_REFERENCE")


@case("E04", "a non-responded survey participation cannot be cited")
def e04(s):
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"survey_participation_id": s.fx["P"]["C3"]["id"], "source_field": "main_benefit", "excerpt": "x", "relationship": "supports"}), 400, "SURVEY_SOURCE_NOT_RESPONDED")


@case("E05", "survey evidence needs a non-blank cited answer")
def e05(s):
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"survey_participation_id": s.fx["P"]["C5"]["id"], "source_field": "main_benefit", "excerpt": "x", "relationship": "supports"}), 400, "SOURCE_FIELD_EMPTY")
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"survey_participation_id": s.fx["P"]["C1"]["id"], "excerpt": "x", "relationship": "supports"}), 400, "INVALID_SOURCE_FIELD")


@case("E06", "source_field must match the source type")
def e06(s):
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"survey_participation_id": s.fx["P"]["C1"]["id"], "source_field": "transcript", "excerpt": "x", "relationship": "supports"}), 400, "INVALID_SOURCE_FIELD")
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"interview_id": s.fx["I1"]["id"], "source_field": "foo", "excerpt": "x", "relationship": "supports"}), 400, "INVALID_SOURCE_FIELD")


@case("E07", "blank excerpts are rejected")
def e07(s):
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"interview_id": s.fx["I1"]["id"], "excerpt": "   ", "relationship": "supports"}), 400, "EXCERPT_REQUIRED")


@case("E08", "supporting and contradicting evidence are both preserved with their sources")
def e08(s):
    sup = ok(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"interview_id": s.fx["I1"]["id"], "source_field": "notes", "excerpt": "Reconciling invoices takes two hours every Friday.", "relationship": "supports"}))
    con = ok(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"survey_participation_id": s.fx["P"]["C5"]["id"], "source_field": "improvement_request", "excerpt": "Needs bank import", "relationship": "contradicts"}))
    s.fx["EV_SUP"], s.fx["EV_CON"] = sup["evidence"], con["evidence"]
    detail = ok(s.owner.call("GET", f"insights/{s.fx['INS']['id']}"))
    rels = sorted(e["relationship"] for e in detail["evidence"])
    expect(rels == ["contradicts", "supports"], f"relationships {rels}")
    kinds = sorted(e["source"]["kind"] for e in detail["evidence"])
    expect(kinds == ["interview", "survey"], f"sources {kinds}")


@case("E09", "identical duplicate evidence is accepted with a warning")
def e09(s):
    r = ok(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/evidence", {"interview_id": s.fx["I1"]["id"], "source_field": "notes", "excerpt": "Reconciling invoices takes two hours every Friday.", "relationship": "supports"}))
    expect(any(w["code"] == "DUPLICATE_EVIDENCE" for w in r["warnings"]), "warning missing")
    s.fx["EV_DUP"] = r["evidence"]


@case("R05", "cited survey responses are locked")
def r05(s):
    ok(s.owner.call("POST", f"survey-waves/{s.fx['W1']['id']}/status", {"action": "reopen"}))
    try:
        rejected(s.owner.call("PATCH", f"participations/{s.fx['P']['C5']['id']}", {"improvement_request": "changed"}), 400, "CITED_CONTENT_LOCKED")
        rejected(s.owner.call("PATCH", f"participations/{s.fx['P']['C5']['id']}", {"clear": ["responded_at", "disappointment_level"]}), 400, "CITED_CONTENT_LOCKED")
    finally:
        ok(s.owner.call("POST", f"survey-waves/{s.fx['W1']['id']}/status", {"action": "close"}))


@case("I02", "an insight with valid evidence can be reviewed")
def i02(s):
    expect(ok(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/review-status", {"review_status": "reviewed"}))["review_status"] == "reviewed", "not reviewed")


@case("I03", "the last evidence of a reviewed insight cannot be deleted")
def i03(s):
    ok(s.owner.call("DELETE", f"evidence/{s.fx['EV_DUP']['id']}"))
    ok(s.owner.call("DELETE", f"evidence/{s.fx['EV_CON']['id']}"))
    rejected(s.owner.call("DELETE", f"evidence/{s.fx['EV_SUP']['id']}"), 400, "LAST_EVIDENCE_OF_REVIEWED_INSIGHT")


@case("V01", "hypotheses require a reviewed insight")
def v01(s):
    draft = ok(s.owner.call("POST", f"products/{s.fx['A']['id']}/insights", {"type": "benefit", "statement": "Draft only"}))
    rejected(s.owner.call("POST", f"insights/{draft['id']}/hypotheses", {"statement": "s", "expected_outcome": "o", "success_metric": "m"}), 400, "INSIGHT_NOT_REVIEWED")
    ok(s.owner.call("DELETE", f"insights/{draft['id']}"))
    s.fx["HYP"] = ok(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/hypotheses", {"statement": "Bank import halves reconciliation time", "expected_outcome": "Weekly reconciliation under 1 hour", "success_metric": "Median minutes per weekly reconciliation"}))
    expect(s.fx["HYP"]["status"] == "proposed" and s.fx["HYP"]["priority"] == "medium", "defaults")


@case("I04", "reviewed insight with hypotheses: statement/type locked; confidence editable")
def i04(s):
    rejected(s.owner.call("PATCH", f"insights/{s.fx['INS']['id']}", {"statement": "Changed"}), 400, "INSIGHT_HAS_HYPOTHESES")
    expect(ok(s.owner.call("PATCH", f"insights/{s.fx['INS']['id']}", {"confidence": "medium"}))["confidence"] == "medium", "confidence")


@case("I05", "an insight with hypotheses cannot return to draft")
def i05(s):
    rejected(s.owner.call("POST", f"insights/{s.fx['INS']['id']}/review-status", {"review_status": "draft"}), 400, "INSIGHT_HAS_HYPOTHESES")


@case("V02", "experiment dates must be ordered")
def v02(s):
    rejected(s.owner.call("POST", f"hypotheses/{s.fx['HYP']['id']}/experiments", {"name": "e", "method": "m", "started_at": s.now - DAY, "ended_at": s.now - 2 * DAY}), 400, "EXPERIMENT_DATES")


@case("V03", "a decision requires a conclusion")
def v03(s):
    rejected(s.owner.call("POST", f"hypotheses/{s.fx['HYP']['id']}/experiments", {"name": "e", "method": "m", "decision": "adopt"}), 400, "EXPERIMENT_DECISION")


@case("V04", "status transitions follow recorded experiments")
def v04(s):
    hid = s.fx["HYP"]["id"]
    rejected(s.owner.call("PATCH", f"hypotheses/{hid}", {"status": "testing"}), 400, "INVALID_STATUS_TRANSITION")
    exp = ok(s.owner.call("POST", f"hypotheses/{hid}/experiments", {"name": "Bank import prototype", "method": "prototype", "started_at": s.now - 3 * DAY, "baseline": "120 min", "target": "< 60 min"}))
    ok(s.owner.call("PATCH", f"hypotheses/{hid}", {"status": "testing"}))
    rejected(s.owner.call("PATCH", f"hypotheses/{hid}", {"status": "validated"}), 400, "INVALID_STATUS_TRANSITION")
    ok(s.owner.call("PATCH", f"experiments/{exp['id']}", {"ended_at": s.now - DAY, "observed_result": "45 min median (synthetic)", "conclusion": "supported", "decision": "adopt"}))
    ok(s.owner.call("PATCH", f"hypotheses/{hid}", {"status": "validated"}))
    rejected(s.owner.call("PATCH", f"experiments/{exp['id']}", {"conclusion": "refuted"}), 400, "HYPOTHESIS_STATUS_DEPENDS")
    s.fx["EXP"] = exp


@case("V05", "experiments and referenced hypotheses are preserved")
def v05(s):
    rejected(s.owner.call("DELETE", f"experiments/{s.fx['EXP']['id']}"), 400, "EXPERIMENT_CONCLUDED")
    rejected(s.owner.call("DELETE", f"hypotheses/{s.fx['HYP']['id']}"), 400, "IN_USE")
    rejected(s.owner.call("DELETE", f"insights/{s.fx['INS']['id']}"), 400, "IN_USE")


# ---------------- Concurrency (U13: must pass before deployment) ----------------
def parallel(calls):
    results = [None] * len(calls)

    def worker(i, fn):
        results[i] = fn()

    threads = [threading.Thread(target=worker, args=(i, fn)) for i, fn in enumerate(calls)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


@case("C01", "parallel duplicate participation: exactly one succeeds")
def c01(s):
    w = s.wave(s.fx["A"]["id"], "C01", "v1", started_days_ago=1)
    cid = s.fx["C7"]["id"]
    rs = parallel([lambda: s.owner.call("POST", f"survey-waves/{w['id']}/participations", {"customer_ids": [cid]})] * 4)
    expect(sum(1 for r in rs if r.status == 200) == 1, f"statuses {[r.status for r in rs]}")
    items = ok(s.owner.call("GET", f"survey-waves/{w['id']}/participations"))["items"]
    expect(len(items) == 1, f"{len(items)} rows")


@case("C02", "parallel deletes cannot remove the last evidence of a reviewed insight")
def c02(s):
    ins = ok(s.owner.call("POST", f"products/{s.fx['A']['id']}/insights", {"type": "obstacle", "statement": "Concurrency probe"}))
    evs = [ok(s.owner.call("POST", f"insights/{ins['id']}/evidence", {"interview_id": s.fx["I2"]["id"], "source_field": "notes", "excerpt": f"probe {i}", "relationship": "supports"}))["evidence"] for i in range(2)]
    ok(s.owner.call("POST", f"insights/{ins['id']}/review-status", {"review_status": "reviewed"}))
    parallel([lambda e=e: s.owner.call("DELETE", f"evidence/{e['id']}") for e in evs])
    remaining = ok(s.owner.call("GET", f"insights/{ins['id']}"))["evidence"]
    expect(len(remaining) >= 1, "reviewed insight lost all evidence")


@case("C03", "closing a wave and editing a response concurrently never writes after close")
def c03(s):
    w = s.wave(s.fx["A"]["id"], "C03", "v1", started_days_ago=1)
    p = s.add(w["id"], [s.fx["C6"]["id"]])[s.fx["C6"]["id"]]
    rs = parallel([
        lambda: s.owner.call("POST", f"survey-waves/{w['id']}/status", {"action": "close"}),
        lambda: s.owner.call("PATCH", f"participations/{p['id']}", {"responded_at": s.now - 60_000, "disappointment_level": "very"}),
    ])
    wave = ok(s.owner.call("GET", f"survey-waves/{w['id']}"))
    row = ok(s.owner.call("GET", f"survey-waves/{w['id']}/participations"))["items"][0]
    if rs[1].status == 200 and row["responded_at"] is not None:
        expect(row["updated_at"] <= wave["closed_at"], "response written after the wave closed")


@case("C04", "creating a hypothesis and unreviewing concurrently never leaves a hypothesis on a draft insight")
def c04(s):
    ins = ok(s.owner.call("POST", f"products/{s.fx['A']['id']}/insights", {"type": "benefit", "statement": "Race probe"}))
    ok(s.owner.call("POST", f"insights/{ins['id']}/evidence", {"interview_id": s.fx["I2"]["id"], "source_field": "notes", "excerpt": "race", "relationship": "supports"}))
    ok(s.owner.call("POST", f"insights/{ins['id']}/review-status", {"review_status": "reviewed"}))
    parallel([
        lambda: s.owner.call("POST", f"insights/{ins['id']}/hypotheses", {"statement": "s", "expected_outcome": "o", "success_metric": "m"}),
        lambda: s.owner.call("POST", f"insights/{ins['id']}/review-status", {"review_status": "draft"}),
    ])
    detail = ok(s.owner.call("GET", f"insights/{ins['id']}"))
    expect(not (detail["review_status"] == "draft" and detail["hypotheses"]), "hypothesis attached to a draft insight")


# ---------------- End to end ----------------
@case("X01", "reload: original evidence and links remain intact")
def x01(s):
    detail = ok(s.owner.call("GET", f"insights/{s.fx['INS']['id']}"))
    expect(detail["review_status"] == "reviewed" and len(detail["evidence"]) >= 1 and detail["hypotheses"], "links lost")
    hyp = ok(s.owner.call("GET", f"hypotheses/{s.fx['HYP']['id']}"))
    expect(hyp["status"] == "validated" and hyp["experiments"][0]["decision"] == "adopt", "validation chain lost")
    interview = ok(s.owner.call("GET", f"interviews/{s.fx['I1']['id']}"))
    expect(interview["notes"] == "  Reconciling invoices takes two hours every Friday.  " and interview["cited"], "raw evidence altered")
    lookups = ok(s.owner.call("GET", f"products/{s.fx['A']['id']}/lookups"))
    expect(any(i["id"] == s.fx["INS"]["id"] for i in lookups["reviewed_insights"]), "lookups missing reviewed insight")


ORDER_PRE = ["S01", "S02"]
RUN_ORDER = [
    "S04", "S05", "M01", "M02", "M03", "M04", "M05", "M06", "M07", "R01", "R04",
    "W01", "W02", "W03", "W04", "W05", "W06", "W07", "W10", "W11",
    "P01", "P02", "P03", "P04", "P05", "P07", "P08", "P09", "W08", "W09",
    "E00", "I01", "E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08", "E09", "S07", "R02", "R03", "R05",
    "I02", "I03", "V01", "I04", "I05", "V02", "V03", "V04", "V05",
    "C01", "C02", "C03", "C04", "X01", "S06",
]
assert sorted(ORDER_PRE + RUN_ORDER) == sorted(t[0] for t in TESTS), "run order must cover every test exactly once"
MANUAL = [
    ("S03", "Unset PMF_OWNER_USER_ID in the isolated tenant: every business endpoint returns 500 OWNER_NOT_CONFIGURED."),
    ("S08", "Inspect isolated request history: sensitive inputs are masked; group history minimized."),
    ("S09", "External call to auth/signup on LIVE remains blocked (UI External Access check; never automated)."),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm-tenant", required=True)
    parser.add_argument("--skip-concurrency", action="store_true")
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    env = os.environ
    try:
        check_config(env.get("PMF_TEST_BASE_URL"), env.get("PMF_TEST_AUTH_URL"), env.get("PMF_TEST_ENV_HOST"),
                     env.get("PMF_TEST_TENANT_NAME"), args.confirm_tenant,
                     env.get("PMF_TEST_OWNER_TOKEN"), env.get("PMF_TEST_INTRUDER_TOKEN"))
    except UnsafeEnvironment as exc:
        print(f"ABORT (configuration): {exc}")
        return 2

    tag = time.strftime("%Y%m%d%H%M%S")
    s = Suite(env["PMF_TEST_BASE_URL"], env["PMF_TEST_AUTH_URL"], env["PMF_TEST_OWNER_TOKEN"], env["PMF_TEST_INTRUDER_TOKEN"], tag)
    owner_me = s.owner_auth.call("GET", "auth/me")
    intruder_me = s.intruder_auth.call("GET", "auth/me")
    products = s.owner.call("GET", "products", params={"per_page": 100})
    try:
        if owner_me.status != 200 or intruder_me.status != 200 or products.status != 200:
            raise UnsafeEnvironment(f"canary requests failed: {owner_me.status}/{intruder_me.status}/{products.status}")
        check_canary(owner_me.body, intruder_me.body, products.body)
    except UnsafeEnvironment as exc:
        print(f"ABORT (canary): {exc}")
        return 2

    only = {t.strip() for t in args.only.split(",") if t.strip()}
    by_id = {t[0]: t for t in TESTS}
    s.run([by_id[t] for t in ORDER_PRE], only)
    try:
        s.build_fixture()
    except Exception as exc:  # noqa: BLE001
        print(f"FIXTURE FAILED: {exc}")
        return 1
    s.run([by_id[t] for t in RUN_ORDER if not (args.skip_concurrency and t.startswith("C"))], only)

    width = max(len(r[2]) for r in s.results) if s.results else 10
    for tid, status, desc, detail in s.results:
        print(f"{status:5} {tid:4} {desc:{width}} {detail}")
    for tid, desc in MANUAL:
        print(f"MANUAL {tid:4} {desc}")
    failed = [r for r in s.results if r[1] != "PASS"]
    print(f"\n{len(s.results) - len(failed)} passed, {len(failed)} failed/error, {len(MANUAL)} manual")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
