#!/usr/bin/env python3
"""Check a saved `xano workspace push --dry-run` preview for the API V1 deployment (offline).

Expected for `-d ./xano/app`: CREATE only — 1 API group, 48 endpoints, 34 functions (83 objects);
no UPDATE/DELETE/TRUNCATE/DROP/ALTER of anything; no table objects; nothing named like the auth endpoints.

Usage: xano workspace push -p pmf -w 2 -b v1 -d ./xano/app --dry-run | tee /tmp/pmf-dry-run.txt
       python3 -I tests/static/check_dry_run.py /tmp/pmf-dry-run.txt
The preview's type labels for API groups/endpoints/functions are not documented; counts are therefore
checked per label and in total, and unknown labels are reported for human review.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP = ROOT / "xano" / "app"
ACTION_RE = re.compile(r"^\s*(CREATE|UPDATE|DELETE|CASCADE_DELETE|TRUNCATE|DROP\w*|ALTER\w*|RENAME\w*)\s+(\S+)\s+(.+?)\s*$")


def expected_objects(app=APP):
    queries = functions = groups = 0
    for f in app.rglob("*.xs"):
        text = f.read_text()
        if re.search(r"^query ", text, re.M):
            queries += 1
        elif re.search(r"^function ", text, re.M):
            functions += 1
        elif re.search(r"^api_group ", text, re.M):
            groups += 1
    return {"api_group": groups, "query": queries, "function": functions}


def check(text, expected):
    problems, by_type = [], {}
    for line in text.splitlines():
        m = ACTION_RE.match(line)
        if not m:
            continue
        action, kind, name = m.groups()
        if action != "CREATE":
            problems.append(f"non-CREATE operation: {line.strip()}")
        if kind.lower() == "table":
            problems.append(f"table change in API deployment: {line.strip()}")
        if re.search(r"auth/(login|me|signup)|Authentication", name):
            problems.append(f"authentication object in preview: {line.strip()}")
        by_type[kind] = by_type.get(kind, 0) + 1
    total = sum(expected.values())
    if sum(by_type.values()) != total:
        problems.append(f"expected {total} CREATE operations, preview lists {sum(by_type.values())}")
    known = {"api_group": ("api_group", "apigroup", "group"), "query": ("query", "api", "endpoint"),
             "function": ("function",)}
    for key, labels in known.items():
        seen = sum(n for k, n in by_type.items() if k.lower() in labels)
        if seen and seen != expected[key]:
            problems.append(f"{key}: expected {expected[key]}, preview lists {seen}")
    unknown = {k: n for k, n in by_type.items() if not any(k.lower() in v for v in known.values())}
    return problems, by_type, unknown


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    expected = expected_objects()
    problems, by_type, unknown = check(pathlib.Path(sys.argv[1]).read_text(), expected)
    print(f"expected: {expected} (total {sum(expected.values())})")
    print(f"preview:  {by_type}")
    if unknown:
        print(f"REVIEW unknown type labels: {unknown}")
    if problems:
        print("FAIL")
        for p in problems:
            print(" -", p)
        return 1
    print("PASS: create-only preview with the expected object counts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
