#!/usr/bin/env python3
"""Check a saved `xano workspace push --dry-run` preview for the API V1 deployment (offline, fail-closed).

Capture the preview WITHOUT losing the CLI's exit status, e.g. (bash or zsh):
    set -o pipefail
    xano workspace push -p pmf -w 2 -b v1 -d ./xano/app --dry-run 2>&1 | tee /tmp/pmf-dry-run.txt
    echo "cli exit: $?"
or without a pipe:
    xano workspace push -p pmf -w 2 -b v1 -d ./xano/app --dry-run > /tmp/pmf-dry-run.txt 2>&1; echo "cli exit: $?"
Then:
    python3 -I tests/static/check_dry_run.py /tmp/pmf-dry-run.txt --cli-exit <that status>

Requirements (from the local sources in xano/app):
  - header `=== Push Preview: workspace 2 ===` and identity line `instance: xgjc-aodb-3a7q.n7e.xano.io | workspace: pmf`
  - a `--- Changes ---` section in which every non-empty line is `<ACTION> <type> <name>`
  - CREATE only; no table changes; no Authentication/auth objects; no unknown resource types
  - exactly: one API group `PMF App` (canonical pmf-app), the 34 local function names, the 48 local endpoints
  - summary `+N created` lines (if shown) must agree with the change list; no updated/deleted summaries

Exit codes: 0 exact inventory verified · 3 structurally valid but objects cannot be uniquely identified
(e.g. endpoints shown without HTTP verbs) — explicit human review required · 1 failed · 2 usage error.
The CLI's type labels for API groups/endpoints/functions are not documented; unrecognized labels FAIL so a
human must review the preview and update this checker deliberately.
"""
import argparse
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP = ROOT / "xano" / "app"
WORKSPACE_ID = "2"
INSTANCE_HOST = "xgjc-aodb-3a7q.n7e.xano.io"
WORKSPACE_NAME = "pmf"
GROUP_NAME, GROUP_CANONICAL = "PMF App", "pmf-app"
ACTIONS = r"CREATE|UPDATE|DELETE|CASCADE_DELETE|TRUNCATE|DROP_FIELD|ALTER_FIELD|DROP|ALTER|RENAME|REPLACE|UPSERT"
CHANGE_RE = re.compile(rf"^\s*({ACTIONS})\s+(\S+)\s+(.+?)\s*$")
HEADER_RE = re.compile(r"^=== Push Preview: workspace (\S+) ===$")
IDENTITY_RE = re.compile(r"^\s*instance:\s*(\S+)\s*\|\s*workspace:\s*(\S+)")
SUMMARY_RE = re.compile(r"^\s*([A-Za-z][A-Za-z _-]*?)\s+((?:[+~\-]\d+\s+\w+[,\s]*)+)$")
TYPE_LABELS = {
    "api_group": {"api_group", "apigroup", "api-group"},
    "query": {"query", "api", "endpoint"},
    "function": {"function"},
}
VERBS = ("GET", "POST", "PATCH", "PUT", "DELETE")
AUTH_RE = re.compile(r"\bauth/(login|me|signup)\b|\bAuthentication\b", re.I)
ERROR_RE = re.compile(r"push blocked|critical error|^\s*error\b|✗|\bfailed\b", re.I)


def expected_inventory(app=APP):
    queries, functions, groups = [], [], []
    for f in sorted(app.rglob("*.xs")):
        text = f.read_text()
        q = re.search(r'^query "([^"]+)" verb=(\w+)', text, re.M)
        fn = re.search(r'^function "([^"]+)"', text, re.M)
        g = re.search(r'^api_group "?([^"{]+?)"? \{', text, re.M)
        if q:
            queries.append((q.group(2), q.group(1)))
        elif fn:
            functions.append(fn.group(1))
        elif g:
            c = re.search(r'canonical = "([^"]+)"', text)
            groups.append((g.group(1).strip(), c.group(1) if c else None))
    return {"api_group": groups, "query": queries, "function": functions}


def expected_objects(app=APP):
    inv = expected_inventory(app)
    return {k: len(v) for k, v in inv.items()}


def kind_of(label):
    for kind, labels in TYPE_LABELS.items():
        if label.lower() in labels:
            return kind
    return None


def parse_query_name(name):
    """Return (verb or None, route) from forms like 'GET products', 'products GET', 'products [GET]'."""
    m = re.fullmatch(rf"({'|'.join(VERBS)})\s+(\S+)", name) or None
    if m:
        return m.group(1), m.group(2)
    m = re.fullmatch(rf"(\S+)\s+[\[(]?({'|'.join(VERBS)})[\])]?", name)
    if m:
        return m.group(2), m.group(1)
    return None, name


def check(text, inventory, cli_exit=0):
    """Returns (status, problems, notes) where status is 0 verified, 3 review required, 1 failed."""
    problems, notes = [], []
    if cli_exit != 0:
        problems.append(f"the dry-run command exited with status {cli_exit}")
    lines = text.splitlines()
    header = next((HEADER_RE.match(l.strip()) for l in lines if HEADER_RE.match(l.strip())), None)
    if not header:
        problems.append("preview header missing (incomplete or unexpected output)")
    elif header.group(1) != WORKSPACE_ID:
        problems.append(f"preview is for workspace {header.group(1)}, expected {WORKSPACE_ID}")
    identity = next((IDENTITY_RE.match(l) for l in lines if IDENTITY_RE.match(l)), None)
    if not identity:
        problems.append("instance/workspace identity line missing")
    elif identity.group(1) != INSTANCE_HOST or identity.group(2) != WORKSPACE_NAME:
        problems.append(f"preview identity {identity.group(1)} / {identity.group(2)} is not {INSTANCE_HOST} / {WORKSPACE_NAME}")
    for l in lines:
        if ERROR_RE.search(l):
            problems.append(f"error reported in preview: {l.strip()}")

    if "--- Changes ---" not in [l.strip() for l in lines]:
        problems.append("changes section missing (incomplete output)")
        return 1, problems, notes
    body = lines[[l.strip() for l in lines].index("--- Changes ---") + 1:]
    head = lines[:[l.strip() for l in lines].index("--- Changes ---")]

    seen = collections.defaultdict(list)
    for l in body:
        if not l.strip():
            continue
        m = CHANGE_RE.match(l)
        if not m:
            problems.append(f"unparseable line in changes section: {l.strip()}")
            continue
        action, label, name = m.groups()
        if action != "CREATE":
            problems.append(f"non-CREATE operation: {l.strip()}")
        if label.lower() == "table":
            problems.append(f"table change in API deployment: {l.strip()}")
        if AUTH_RE.search(name):
            problems.append(f"authentication object in preview: {l.strip()}")
        kind = kind_of(label)
        if kind is None:
            problems.append(f"unknown resource type '{label}': {l.strip()}")
            continue
        seen[kind].append(name)

    created_lines = sum(len(v) for v in seen.values())
    summary_created = 0
    for l in head:
        m = SUMMARY_RE.match(l)
        if not m:
            continue
        for sign, count, word in re.findall(r"([+~\-])(\d+)\s+(\w+)", m.group(2)):
            if sign == "+" and word == "created":
                summary_created += int(count)
            else:
                problems.append(f"summary reports non-create changes: {l.strip()}")
    if summary_created and summary_created != created_lines:
        problems.append(f"summary says {summary_created} created but {created_lines} change lines are listed")

    exp_groups = inventory["api_group"]
    if sorted(seen["api_group"]) not in ([g[0] for g in exp_groups], [g[1] for g in exp_groups]) \
            or exp_groups != [(GROUP_NAME, GROUP_CANONICAL)]:
        problems.append(f"API groups {seen['api_group']} != expected {exp_groups}")
    if collections.Counter(seen["function"]) != collections.Counter(inventory["function"]):
        missing = collections.Counter(inventory["function"]) - collections.Counter(seen["function"])
        extra = collections.Counter(seen["function"]) - collections.Counter(inventory["function"])
        problems.append(f"functions differ: missing {sorted(missing)} extra {sorted(extra)}")

    parsed = [parse_query_name(n) for n in seen["query"]]
    exp_q = collections.Counter(inventory["query"])
    if all(v is not None for v, _ in parsed) and parsed:
        got = collections.Counter(parsed)
        if got != exp_q:
            problems.append(f"endpoints differ: missing {sorted(exp_q - got)} extra {sorted(got - exp_q)}")
        exact = True
    else:
        got_routes = collections.Counter(r for _, r in parsed)
        exp_routes = collections.Counter(r for _, r in inventory["query"])
        if got_routes != exp_routes:
            problems.append(f"endpoint routes differ: missing {sorted(exp_routes - got_routes)} extra {sorted(got_routes - exp_routes)}")
        exact = False
        notes.append("endpoints are listed without HTTP verbs: routes match by count, but individual endpoints "
                     "(e.g. GET vs POST products) cannot be uniquely identified — explicit human review required")
    if problems:
        return 1, problems, notes
    return (0 if exact else 3), problems, notes


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("preview")
    parser.add_argument("--cli-exit", type=int, required=True, help="exit status of the dry-run command")
    args = parser.parse_args()
    inventory = expected_inventory()
    status, problems, notes = check(pathlib.Path(args.preview).read_text(), inventory, args.cli_exit)
    print(f"expected: {expected_objects()} (total {sum(expected_objects().values())})")
    for n in notes:
        print(f"REVIEW {n}")
    if status == 1:
        print("FAIL")
        for p in problems:
            print(" -", p)
    elif status == 3:
        print("REVIEW REQUIRED: structure and counts match, exact endpoint identity not verifiable from this preview")
    else:
        print("PASS: create-only preview with the exact expected inventory (1 group, 48 endpoints, 34 functions)")
    return status


if __name__ == "__main__":
    sys.exit(main())
