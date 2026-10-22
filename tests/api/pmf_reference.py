"""Reference implementation of the PMF scoring contract (docs/03, D-006, D-022, Appendix R8).

Used by the HTTP suite to derive expected values and by offline unit tests.
"""


def count_rows(rows):
    valid = [r for r in rows if r.get("responded_at") is not None and r.get("disappointment_level") is not None]
    invited = [r for r in rows if r.get("invited_at") is not None]
    invited_valid = [r for r in valid if r.get("invited_at") is not None]
    return {
        "eligible_count": len(rows),
        "invited_count": len(invited),
        "responded_count": sum(1 for r in rows if r.get("responded_at") is not None),
        "valid_response_count": len(valid),
        "incomplete_response_count": sum(1 for r in rows if r.get("responded_at") is not None and r.get("disappointment_level") is None),
        "anomaly_count": sum(1 for r in rows if r.get("responded_at") is None and r.get("disappointment_level") is not None),
        "very_count": sum(1 for r in valid if r["disappointment_level"] == "very"),
        "somewhat_count": sum(1 for r in valid if r["disappointment_level"] == "somewhat"),
        "not_count": sum(1 for r in valid if r["disappointment_level"] == "not"),
        "invited_valid_count": len(invited_valid),
        "manual_valid_count": len(valid) - len(invited_valid),
    }


def compute(counts, small_sample_threshold=30):
    valid = counts["valid_response_count"]
    pmf = (counts["very_count"] * 100.0 / valid) if valid > 0 else None
    rate = (counts["invited_valid_count"] / counts["invited_count"]) if counts["invited_count"] > 0 else None
    return {"pmf_percent": pmf, "invited_response_rate": rate, "small_sample": valid < small_sample_threshold}


# Fixture wave W1 (docs/08): 5 eligible, 4 invited, 3 valid (1 very, 1 somewhat, 1 not), 2 nonrespondents.
# C5 answered without an invitation (manual entry) so the invited response rate is 2/4.
W1_ROWS = [
    {"customer": "C1", "segment": "A1", "invited_at": 1, "responded_at": 2, "disappointment_level": "very"},
    {"customer": "C2", "segment": "A1", "invited_at": 1, "responded_at": 2, "disappointment_level": "somewhat"},
    {"customer": "C3", "segment": "A2", "invited_at": 1, "responded_at": None, "disappointment_level": None},
    {"customer": "C4", "segment": "A2", "invited_at": 1, "responded_at": None, "disappointment_level": None},
    {"customer": "C5", "segment": None, "invited_at": None, "responded_at": 2, "disappointment_level": "not"},
]
