"""Offline regression checks for the 2026-10-23 live-run failures (no network, no Xano).

Each test replays the faulty server behaviour observed in the live run against the real HTTP-suite case and
requires the case to FAIL, then replays the corrected behaviour and requires it to PASS. This shows the
assertions detect the original defects without weakening them.

Run: python3 -m unittest discover -s tests/api -p 'test_offline*.py'
"""
import unittest

import pmf_api_tests as suite
from http_client import Response

CASES = {tid: fn for tid, _desc, fn in suite.TESTS}
DAY = 86_400_000


class Owner:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def call(self, method, path, body=None, params=None):
        self.calls.append((method, path, body, params))
        status, out = self.handler(method, path, body or {}, params or {})
        return Response(status, out)


class Session:
    def __init__(self, handler, fx):
        self.owner = Owner(handler)
        self.fx = fx
        self.now = 1_800_000_000_000

    def report(self, wid, **params):
        return suite.ok(self.owner.call("GET", f"survey-waves/{wid}/report", params=params or None))


def err(status, message):
    return status, {"code": "ERROR_CODE_INPUT_ERROR" if status == 400 else "ERROR_FATAL", "message": message}


class Regressions(unittest.TestCase):
    def run_case(self, tid, handler, fx):
        CASES[tid](Session(handler, fx))

    # ---------- P06: report counts are nested under `counts` ----------
    def p06_handler(self, very):
        def handler(method, path, body, params):
            if method == "PATCH":
                return 200, {}
            if params.get("segment_id") == 2:
                return 200, {"selected": {"valid_response_count": 0, "pmf_percent": None, "counts": {"very": 0, "somewhat": 0, "not": 0}}}
            return 200, {"selected": {"valid_response_count": 2, "pmf_percent": 50.0, "counts": {"very": very, "somewhat": 1, "not": 0}}}
        return handler

    def test_p06(self):
        fx = {"W1": {"id": 1}, "C1": {"id": 1}, "A1": {"id": 1}, "A2": {"id": 2}}
        self.run_case("P06", self.p06_handler(1), fx)
        with self.assertRaises(suite.Failure):  # expected value not weakened: a lost snapshot response still fails
            self.run_case("P06", self.p06_handler(0), fx)

    # ---------- P09: empty recent experiments ----------
    def p09_handler(self, overview_status):
        def handler(method, path, body, params):
            if path.endswith("/overview"):
                if overview_status == 500:
                    return err(500, "Unable to locate var: recent_experiments.items")
                return 200, {"waves": [{"wave": {"name": n}} for n in ("W1", "W2", "W3")], "customers": {"total": 7}, "recent_experiments": []}
            if path.endswith("/lookups"):
                return 200, {"segments": [{"id": 3}], "waves": [], "reviewed_insights": []}
            raise AssertionError(path)
        return handler

    def test_p09(self):
        fx = {"A": {"id": 1}, "B": {"id": 2}}
        with self.assertRaises(suite.Failure):
            self.run_case("P09", self.p09_handler(500), fx)
        self.run_case("P09", self.p09_handler(200), fx)

    # ---------- W08: close without closed_at ----------
    def w08_handler(self, original_bug):
        state = {"closed": False}

        def handler(method, path, body, params):
            if path.endswith("/status"):
                closed_at = body.get("closed_at")
                if state["closed"]:
                    return err(400, "WAVE_ALREADY_CLOSED: the survey wave is already closed")
                if closed_at is not None and closed_at > suite.time.time() * 1000:
                    return err(400, "INVALID_TIMESTAMP: closed_at must not be in the future")
                if closed_at is None and original_bug:
                    return err(400, "INVALID_TIMESTAMP: closed_at must not be in the future")
                if closed_at is not None:
                    return err(400, "INVALID_TIMESTAMP: closed_at must not precede the latest recorded response")
                state["closed"] = True
                return 200, {"state": "closed", "closed_at": int(suite.time.time() * 1000)}
            return err(400, "WAVE_CLOSED: the survey wave is closed")
        return handler

    def test_w08(self):
        fx = {"W1": {"id": 1}, "C6": {"id": 6}, "P": {"C3": {"id": 3}, "C4": {"id": 4}}}
        with self.assertRaises(suite.Failure):
            self.run_case("W08", self.w08_handler(True), fx)
        self.run_case("W08", self.w08_handler(False), fx)

    def test_w08_rejects_accepting_a_future_close(self):
        fx = {"W1": {"id": 1}, "C6": {"id": 6}, "P": {"C3": {"id": 3}, "C4": {"id": 4}}}
        state = {"closed": False}

        def lenient(method, path, body, params):  # a server that accepts any closed_at must fail W08
            if path.endswith("/status"):
                if state["closed"]:
                    return err(400, "WAVE_ALREADY_CLOSED: x")
                if body.get("closed_at") is not None and body["closed_at"] < 1_900_000_000_000:
                    return err(400, "INVALID_TIMESTAMP: closed_at must not precede the latest recorded response")
                state["closed"] = True
                return 200, {"state": "closed", "closed_at": body.get("closed_at") or int(suite.time.time() * 1000)}
            return err(400, "WAVE_CLOSED: x")
        with self.assertRaises(suite.Failure):
            self.run_case("W08", lenient, fx)

    # ---------- X02: explicit clear on product PATCH ----------
    def test_x02_detects_missing_explicit_clear(self):
        product = {"name": "SYNTH A", "description": None}

        def handler(method, path, body, params):  # deployed behaviour: no `clear` input, so it is ignored
            if path == "products/1" and method == "GET":
                return 200, dict(product, counts={"segments": 2, "customers": 7, "interviews": 2})
            if path == "products/1" and method == "PATCH":
                for k, v in body.items():
                    if k in product and v is not None and str(v).strip():
                        product[k] = v
                return 200, dict(product)
            raise AssertionError(path)
        with self.assertRaises(suite.Failure) as ctx:
            self.run_case("X02", handler, {"A": {"id": 1}})
        self.assertIn("explicit clear", str(ctx.exception))


class StrictConcurrencyOutcomes(unittest.TestCase):
    """C02/C04 outcome checks: only the single serialized outcome passes; 500s and ambiguity fail."""
    CTX = {"insight": 9, "evidence": [11, 12]}

    @staticmethod
    def r(status, message=None, body=None):
        return Response(status, body if body is not None else ({"message": message} if message else {"deleted": True}))

    def detail(self, status, evidence_ids, hyps=()):
        return {"review_status": status, "evidence": [{"id": i, "relationship": "supports"} for i in evidence_ids],
                "hypotheses": [{"id": h} for h in hyps]}

    def test_c02_serialized_outcome_passes(self):
        last = "LAST_EVIDENCE_OF_REVIEWED_INSIGHT: move the insight back to draft"
        self.assertIsNone(suite.c02_outcome(self.CTX, [self.r(200), self.r(400, last)], self.detail("reviewed", [12])))
        self.assertIsNone(suite.c02_outcome(self.CTX, [self.r(400, last), self.r(200)], self.detail("reviewed", [11])))

    def test_c02_failures(self):
        last = "LAST_EVIDENCE_OF_REVIEWED_INSIGHT: x"
        cases = [
            ([self.r(200), self.r(200)], self.detail("reviewed", [])),                       # both succeed (observed live)
            ([self.r(200), self.r(500, "Unable to locate var: x")], self.detail("reviewed", [12])),  # HTTP 500
            ([self.r(500, "boom"), self.r(500, "boom")], self.detail("reviewed", [11, 12])),
            ([self.r(400, last), self.r(400, last)], self.detail("reviewed", [11, 12])),     # both fail
            ([self.r(200), self.r(400, "NOT_FOUND: evidence")], self.detail("reviewed", [12])),  # wrong reason
            ([self.r(200), self.r(400, last)], self.detail("reviewed", [11])),               # wrong row kept
            ([self.r(200), self.r(400, last)], self.detail("draft", [12])),                  # status changed
        ]
        for rs, detail in cases:
            self.assertIsNotNone(suite.c02_outcome(self.CTX, rs, detail), (rs, detail))

    def test_c04_serialized_outcomes_pass(self):
        made = self.r(200, body={"id": 5})
        self.assertIsNone(suite.c04_outcome([made, self.r(400, "INSIGHT_HAS_HYPOTHESES: x")], self.detail("reviewed", [1], [5])))
        self.assertIsNone(suite.c04_outcome([self.r(400, "INSIGHT_NOT_REVIEWED: x"), self.r(200, body={"id": 9})], self.detail("draft", [1])))

    def test_c04_failures(self):
        made = self.r(200, body={"id": 5})
        cases = [
            ([made, self.r(200, body={"id": 9})], self.detail("draft", [1], [5])),           # both succeed (observed live)
            ([made, self.r(500, "Unable to locate var: x")], self.detail("reviewed", [1], [5])),  # HTTP 500
            ([self.r(500, "boom"), self.r(200, body={"id": 9})], self.detail("draft", [1])),
            ([self.r(400, "INSIGHT_NOT_REVIEWED: x"), self.r(400, "INSIGHT_HAS_HYPOTHESES: x")], self.detail("reviewed", [1])),
            ([made, self.r(400, "NO_STATUS_CHANGE: x")], self.detail("reviewed", [1], [5])),     # wrong reason
            ([self.r(400, "INSIGHT_HAS_HYPOTHESES: x"), self.r(200, body={"id": 9})], self.detail("draft", [1])),
            ([made, self.r(400, "INSIGHT_HAS_HYPOTHESES: x")], self.detail("draft", [1], [5])),  # final state wrong
            ([self.r(400, "INSIGHT_NOT_REVIEWED: x"), self.r(200, body={"id": 9})], self.detail("draft", [1], [5])),
        ]
        for rs, detail in cases:
            self.assertIsNotNone(suite.c04_outcome(rs, detail), (rs, detail))


if __name__ == "__main__":
    unittest.main()
