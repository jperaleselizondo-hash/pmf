#!/usr/bin/env python3
"""Compare a post-deployment pull of workspace 2 with the committed sources (offline).

  python3 -I tests/static/compare_readback.py <pulled-after-dir> [--baseline <pulled-before-dir>] [--json <out>]

Result classes per deployed object:
  EQUIVALENT  identical after DOCUMENTED, semantics-preserving Xano re-formatting only (see EQUIVALENCES)
  RUNTIME     differs in a way that is plausibly the server's canonical form but cannot be proven equivalent
              offline; each item names the runtime test gate that must prove it (never silently equivalent)
  UNEXPLAINED anything else — structural failure

Exit 0 = structural verification passed (no missing/extra/unexplained objects, GUIDs match, baseline
unchanged); RUNTIME items are then printed as outstanding runtime gates. Exit 1 = structural failure.
Never adopt the pulled text as source: the server prints some expressions without the parentheses that
XanoScript's greedy filter binding needs, so the committed source stays authoritative.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP = ROOT / "xano" / "app"

EQUIVALENCES = [
    "comments, guid lines and field `description` attributes (descriptions are rendered as comments)",
    "quoted vs unquoted construct names (e.g. `query \"products\"` vs `query products`)",
    "whitespace, line breaks, column alignment, commas and string quotes",
    "`type: \"inner\"` in joins (default join type)",
    "`error_type = \"standard\"` (default error type)",
    "`expect.to_throw` vs `expect.to_throw { exception = \"\" }`",
    "api_group attribute order",
    "parentheses around a complete object-literal value (`key: ($x|count)` at end of the value)",
    "parentheses around an atomic filter argument at the end of a value (`|set:\"k\":($var)`, `|push:($row)`)",
]

# Runtime gates for known RUNTIME classes; keyed by (class, object key) or class alone.
GATES = {
    ("missing_default", None): "P02/P03 (omitted `unsegmented` must behave as false), P09 overview summaries, W03/X02 participation listing",
    ("expression_mode", ("query", "hypotheses/{hypothesis_id}/experiments", "POST")): "V02, V03, V04 (experiment validation and persisted fields on create)",
    ("test_expression_block", None): "server-side inline unit tests: `xano unit_test run_all -p pmf -w 2 -b v1` (count_wave fixtures)",
    ("grouping", ("function", "pmf/evidence/validate_source")): "E05, E06, E08 (survey source_field validation)",
    ("grouping", ("query", "survey-waves/{wave_id}/participations", "GET")): "X02 participation pagination (page/per_page slice)",
}


def key_of(text):
    for pattern, kind in ((r'^query "?([^"\s]+)"? verb=(\w+)', "query"), (r'^function "?([^"\s]+)"?', "function"),
                          (r'^api_group "?([^"{]+?)"? \{', "api_group")):
        m = re.search(pattern, text, re.M)
        if m:
            return (kind,) + tuple(g.strip() for g in m.groups())
    return None


def guid_of(text):
    m = re.search(r'^\s*guid = "([^"]+)"', text, re.M)
    return m.group(1) if m else None


def strip_noise(text):
    text = re.sub(r"^\s*//.*$", "", text, flags=re.M)
    text = re.sub(r'^\s*guid = "[^"]*"\s*$', "", text, flags=re.M)
    text = re.sub(r'^\s*description = "[^"]*"\s*$', "", text, flags=re.M)
    text = re.sub(r'\bdescription = "[^"]*"', "", text)
    text = re.sub(r'^(query|function|api_group) "([^"]+)"', r"\1 \2", text, flags=re.M)
    text = re.sub(r'\btype\s*:\s*"inner"\s*,?', "", text)
    text = re.sub(r'^\s*error_type = "standard"\s*$', "", text, flags=re.M)
    text = re.sub(r'expect\.to_throw\s*\{\s*exception\s*=\s*""\s*\}', "expect.to_throw", text)
    return text


VALUE_PAREN = re.compile(r'^(\s*"?[A-Za-z_]\w*"?\s*:\s*)\((\$[\w.]+(?:\|\w+(?::(?:"[^"]*"|\$[\w.]+|\d+))*)*)\)(\s*,?\s*)$', re.M)
ARG_PAREN = re.compile(r'(\|\w+(?::(?:"[^"]*"|\$[\w.]+|\d+))*:)\((\$[\w.]+)\)(\s*)$', re.M)


def strip_safe_parens(text):
    text = VALUE_PAREN.sub(r"\1\2\3", text)
    return ARG_PAREN.sub(r"\1\2\3", text)


def collapse(text):
    return re.sub(r'[\s",]', "", text)


def api_group_attrs(text):
    body = text[text.index("{") + 1:text.rindex("}")]
    return sorted(collapse(line) for line in strip_noise(body).splitlines() if collapse(line))


def canonical(text):
    return collapse(strip_safe_parens(strip_noise(text)))


def classify(key, local, pulled):
    """Return (status, items) where items are (class, detail)."""
    if key[0] == "api_group":
        return ("EQUIVALENT", []) if api_group_attrs(local) == api_group_attrs(pulled) else ("UNEXPLAINED", [("api_group", "attributes differ")])
    a, b = canonical(local), canonical(pulled)
    if a == b:
        return "EQUIVALENT", []
    items = []
    stripped_local = strip_safe_parens(strip_noise(local))
    stripped_pulled = strip_safe_parens(strip_noise(pulled))
    defaults = re.findall(r"\bbool\??\s+(\w+)\?=false", stripped_local)
    if defaults and not re.search(r"=false", stripped_pulled):
        stripped_local = re.sub(r"(\bbool\??\s+\w+\?)=false", r"\1", stripped_local)
        items.append(("missing_default", f"bool default false dropped for: {', '.join(defaults)}"))
    if "```" in stripped_pulled:
        stripped_pulled = stripped_pulled.replace("```", "")
        items.append(("test_expression_block", "inline test input stored as an expression block"))
    if re.search(r"`[^`]+`", stripped_pulled):
        stripped_pulled = re.sub(r"`([^`]+)`", r"\1", stripped_pulled)
        items.append(("expression_mode", "value stored in backtick expression mode"))
    a, b = collapse(stripped_local), collapse(stripped_pulled)
    if a != b and a.replace("(", "").replace(")", "") == b.replace("(", "").replace(")", ""):
        snippets = []
        for line in stripped_local.splitlines():
            if "(" in line and collapse(line) not in b:
                snippets.append(line.strip()[:120])
        items.append(("grouping", "parentheses dropped inside an expression: " + " | ".join(snippets[:3])))
        a = b
    if a != b:
        return "UNEXPLAINED", items + [("diff", "unexplained structural difference")]
    return "RUNTIME", items


def collect(root, only_pmf=False):
    out = {}
    for f in pathlib.Path(root).rglob("*.xs"):
        text = f.read_text()
        key = key_of(text)
        if not key:
            continue
        if only_pmf and not ((key[0] == "function" and key[1].startswith("pmf/")) or key == ("api_group", "PMF App")
                             or re.search(r'^\s*api_group = "PMF App"$', text, re.M)):
            continue
        out[key] = text
    return out


def compare(after, baseline=None, app=APP):
    local, pulled = collect(app), collect(after, only_pmf=True)
    report = {"structural_problems": [], "objects": {}, "runtime_gates": []}
    for key, text in sorted(local.items()):
        if key not in pulled:
            report["structural_problems"].append(f"missing in Xano: {key}")
            continue
        lg, pg = guid_of(text), guid_of(pulled[key])
        if lg is None or lg != pg:
            report["structural_problems"].append(f"guid mismatch for {key}: local {lg} vs deployed {pg}")
        status, items = classify(key, text, pulled[key])
        report["objects"][" ".join(key)] = {"status": status, "items": items}
        if status == "UNEXPLAINED":
            report["structural_problems"].append(f"unexplained difference: {key} {items}")
        for cls, detail in items:
            gate = GATES.get((cls, key)) or GATES.get((cls, None)) or "REQUIRES MANUAL REVIEW (no runtime gate mapped)"
            report["runtime_gates"].append({"object": " ".join(key), "class": cls, "detail": detail, "gate": gate})
    for key in sorted(set(pulled) - set(local)):
        report["structural_problems"].append(f"unexpected PMF object in Xano: {key}")
    if baseline:
        for f in sorted(pathlib.Path(baseline).rglob("*.xs")):
            rel = f.relative_to(baseline)
            g = pathlib.Path(after) / rel
            if not g.exists() or g.read_bytes() != f.read_bytes():
                report["structural_problems"].append(f"pre-existing document changed: {rel}")
        before_n = sum(1 for _ in pathlib.Path(baseline).rglob("*.xs"))
        after_n = sum(1 for _ in pathlib.Path(after).rglob("*.xs"))
        if after_n != before_n + len(local):
            report["structural_problems"].append(f"document count {after_n} != {before_n} existing + {len(local)} new")
    report["counts"] = {
        "local": len(local), "deployed_pmf": len(pulled),
        "equivalent": sum(1 for o in report["objects"].values() if o["status"] == "EQUIVALENT"),
        "runtime": sum(1 for o in report["objects"].values() if o["status"] == "RUNTIME"),
        "unexplained": sum(1 for o in report["objects"].values() if o["status"] == "UNEXPLAINED"),
    }
    return report


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    after = args[0]
    baseline = args[args.index("--baseline") + 1] if "--baseline" in args else None
    report = compare(after, baseline)
    if "--json" in args:
        pathlib.Path(args[args.index("--json") + 1]).write_text(json.dumps(report, indent=2))
    c = report["counts"]
    print(f"local objects: {c['local']}; deployed PMF objects: {c['deployed_pmf']}")
    print(f"EQUIVALENT {c['equivalent']} · RUNTIME {c['runtime']} · UNEXPLAINED {c['unexplained']}")
    for gate in report["runtime_gates"]:
        print(f"RUNTIME GATE  {gate['object']}: {gate['class']} — {gate['detail']}\n              → {gate['gate']}")
    if report["structural_problems"]:
        print("FAIL (structural)")
        for p in report["structural_problems"]:
            print(" -", p)
        return 1
    print("PASS (structural)" + (" — pre-existing documents unchanged" if baseline else "")
          + (f"; runtime equivalence NOT established for {c['runtime']} object(s) — see RUNTIME GATE lines" if c["runtime"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
