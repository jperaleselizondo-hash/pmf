"""Offline unit tests (no network): safety guard and PMF reference values.

Run: python3 -I -m unittest discover -s tests/api -p 'test_offline.py'
"""
import unittest

import pmf_reference as ref
from safety import UnsafeEnvironment, check_canary, check_config

ISO_HOST = "pmf-api-test.example-tenant.xano.io"
GOOD = dict(
    base_url=f"https://{ISO_HOST}/api:pmf-app",
    auth_url=f"https://{ISO_HOST}/api:auth-canonical",
    env_host=ISO_HOST,
    tenant_name="pmf-api-test",
    confirm_tenant="pmf-api-test",
    owner_token="owner-token-placeholder",
    intruder_token="intruder-token-placeholder",
)


class SafetyConfig(unittest.TestCase):
    def test_good_config_passes(self):
        self.assertEqual(check_config(**GOOD), ISO_HOST)

    def test_live_host_is_refused(self):
        bad = dict(GOOD, base_url="https://xgjc-aodb-3a7q.n7e.xano.io/api:pmf-app", env_host="xgjc-aodb-3a7q.n7e.xano.io")
        with self.assertRaises(UnsafeEnvironment):
            check_config(**bad)

    def test_live_auth_host_is_refused(self):
        bad = dict(GOOD, auth_url="https://xgjc-aodb-3a7q.n7e.xano.io/api:x")
        with self.assertRaises(UnsafeEnvironment):
            check_config(**bad)

    def test_host_must_match_isolated_tenant(self):
        with self.assertRaises(UnsafeEnvironment):
            check_config(**dict(GOOD, env_host="other.xano.io"))

    def test_tenant_confirmation_required(self):
        with self.assertRaises(UnsafeEnvironment):
            check_config(**dict(GOOD, confirm_tenant="something-else"))

    def test_canonical_path_required(self):
        with self.assertRaises(UnsafeEnvironment):
            check_config(**dict(GOOD, base_url=f"https://{ISO_HOST}/api:other"))

    def test_https_required(self):
        with self.assertRaises(UnsafeEnvironment):
            check_config(**dict(GOOD, base_url=f"http://{ISO_HOST}/api:pmf-app"))

    def test_missing_token(self):
        with self.assertRaises(UnsafeEnvironment):
            check_config(**dict(GOOD, owner_token=""))

    def test_same_tokens_refused(self):
        with self.assertRaises(UnsafeEnvironment):
            check_config(**dict(GOOD, intruder_token=GOOD["owner_token"]))


class SafetyCanary(unittest.TestCase):
    OWNER = {"id": 1, "email": "owner@pmf-test.invalid"}
    INTRUDER = {"id": 2, "email": "intruder@pmf-test.invalid"}

    def test_synthetic_environment_passes(self):
        self.assertTrue(check_canary(self.OWNER, self.INTRUDER, {"items": [{"name": "SYNTH-x-A"}]}))

    def test_real_owner_email_refused(self):
        with self.assertRaises(UnsafeEnvironment):
            check_canary({"id": 1, "email": "someone@example.com"}, self.INTRUDER, {"items": []})

    def test_non_synthetic_product_refused(self):
        with self.assertRaises(UnsafeEnvironment):
            check_canary(self.OWNER, self.INTRUDER, {"items": [{"name": "Real product"}]})

    def test_same_user_refused(self):
        with self.assertRaises(UnsafeEnvironment):
            check_canary(self.OWNER, dict(self.OWNER), {"items": []})


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
