"""Repeated, barrier-synchronized race trials for the U13 concurrency gate (C01–C04).

A parent-row no-op update is NOT assumed to lock anything. Each invariant is exercised in many fresh
trials; all workers are released together by a barrier; client-side request intervals are recorded.

Gate semantics (any failure blocks deployment):
- FAIL if any trial violates its final-state invariant.
- FAIL (inconclusive) if fewer than `min_overlap_ratio` of trials had all requests in flight at the same
  time on the client side — without overlap a passing result proves nothing about concurrency.
Client-side overlap is necessary but not sufficient evidence of server-side interleaving; the report
records timings so the operator can judge, and a pass is still only evidence for the observed trials.
"""
import threading
import time


class RaceResult:
    def __init__(self, name):
        self.name = name
        self.trials = []
        self.violations = []

    @property
    def overlap_ratio(self):
        if not self.trials:
            return 0.0
        return sum(1 for t in self.trials if t["overlap"]) / len(self.trials)

    def summary(self):
        codes = {}
        for t in self.trials:
            key = tuple(t["statuses"])
            codes[key] = codes.get(key, 0) + 1
        return f"{len(self.trials)} trials, overlap {self.overlap_ratio:.0%}, outcomes {codes}, violations {len(self.violations)}"


def _overlap(intervals):
    return max(start for start, _ in intervals) < min(end for _, end in intervals)


def run_trials(name, trials, setup, actions, invariant, clock=time.monotonic):
    """setup() -> ctx; actions: list of callables (ctx) -> Response; invariant(ctx, responses) -> None or message."""
    result = RaceResult(name)
    for index in range(trials):
        ctx = setup(index)
        barrier = threading.Barrier(len(actions))
        responses = [None] * len(actions)
        intervals = [None] * len(actions)
        errors = []

        def worker(i, action):
            try:
                barrier.wait(timeout=30)
                start = clock()
                responses[i] = action(ctx)
                intervals[i] = (start, clock())
            except Exception as exc:  # noqa: BLE001 - recorded as a trial error
                errors.append(f"{type(exc).__name__}: {exc}")

        threads = [threading.Thread(target=worker, args=(i, a)) for i, a in enumerate(actions)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if errors or any(i is None for i in intervals):
            result.violations.append(f"trial {index}: request error {errors}")
            continue
        overlap = _overlap(intervals)
        message = invariant(ctx, responses)
        result.trials.append({"statuses": [r.status for r in responses], "overlap": overlap, "intervals": intervals})
        if message:
            result.violations.append(f"trial {index}: {message}")
    return result


def gate(result, min_overlap_ratio=0.8):
    """Return None when the concurrency gate passes, else a failure message."""
    if result.violations:
        return f"INVARIANT VIOLATED ({result.summary()}): {result.violations[:3]}"
    if result.overlap_ratio < min_overlap_ratio:
        return f"INCONCLUSIVE: insufficient concurrent overlap ({result.summary()})"
    return None
