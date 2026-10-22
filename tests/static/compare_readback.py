#!/usr/bin/env python3
"""Compare a post-deployment pull of workspace 2 with the local sources (offline).

  python3 -I tests/static/compare_readback.py <pulled-after-dir> [--baseline <pulled-before-dir>]

Checks:
  - every local API group / endpoint / function under xano/app exists in the pull with the same
    structure (comments, guid lines, whitespace, quotes and commas ignored; description attributes are
    rendered as comments by the server, so they are compared as text separately)
  - the pull contains no PMF App objects that are missing locally
  - with --baseline: every document present before deployment is byte-identical afterwards
    (tables, `user`, Authentication group and auth endpoints, workspace settings)
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP = ROOT / "xano" / "app"


def key_of(text):
    for pattern, kind in ((r'^query "([^"]+)" verb=(\w+)', "query"), (r'^function "([^"]+)"', "function"),
                          (r'^api_group "?([^"{]+?)"? \{', "api_group")):
        m = re.search(pattern, text, re.M)
        if m:
            return (kind,) + tuple(g.strip() for g in m.groups())
    return None


def normalize(text):
    text = re.sub(r'description = "([^"]*)"', "", text)
    text = re.sub(r"^\s*//.*$", "", text, flags=re.M)
    text = re.sub(r'^\s*guid = "[^"]*"\s*$', "", text, flags=re.M)
    text = re.sub(r"\{\s*\}", "", text)
    return re.sub(r"[\s\",]", "", text)


def descriptions(text):
    found = set(re.findall(r'description = "([^"]*)"', text))
    found |= {m.strip() for m in re.findall(r"^\s*//\s*(.+)$", text, flags=re.M)}
    return found


def collect(root, only_pmf=False):
    out = {}
    for f in pathlib.Path(root).rglob("*.xs"):
        text = f.read_text()
        key = key_of(text)
        if not key:
            continue
        if only_pmf and not (key[0] == "function" and key[1].startswith("pmf/")) and \
                not re.search(r'api_group = "PMF App"', text) and key != ("api_group", "PMF App"):
            continue
        out[key] = text
    return out


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    after = pathlib.Path(args[0])
    baseline = pathlib.Path(args[args.index("--baseline") + 1]) if "--baseline" in args else None
    local = collect(APP)
    pulled = collect(after, only_pmf=True)
    problems = []
    for key, text in local.items():
        if key not in pulled:
            problems.append(f"missing in Xano: {key}")
        elif normalize(text) != normalize(pulled[key]):
            problems.append(f"structure differs: {key}")
        elif not descriptions(text) <= descriptions(pulled[key]):
            problems.append(f"descriptions differ: {key}")
    for key in pulled:
        if key not in local:
            problems.append(f"unexpected PMF object in Xano: {key}")
    if baseline:
        for f in baseline.rglob("*.xs"):
            rel = f.relative_to(baseline)
            g = after / rel
            if not g.exists() or g.read_bytes() != f.read_bytes():
                problems.append(f"pre-existing document changed: {rel}")
    print(f"local objects: {len(local)}; PMF objects in pull: {len(pulled)}")
    if problems:
        print("FAIL")
        for p in problems:
            print(" -", p)
        return 1
    print("PASS: read-back matches local sources" + (" and pre-existing documents are unchanged" if baseline else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
