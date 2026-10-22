#!/usr/bin/env python3
"""Static checks for the PMF Engine API sources in xano/app (offline; no network, no Xano access).

Complements the XanoScript syntax validator with project rules from docs/API_V1_PROPOSAL.md (Appendix R8):
inventory, owner guard, access loaders, route collisions, table/field references, sensitive inputs,
mass-assignment, error codes, pagination and forbidden constructs.

Usage: python3 -I tests/static/xs_api_lint.py [repo_root]
Exit code 0 = all checks pass.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
APP = ROOT / "xano" / "app"
TABLE_DIRS = [ROOT / "xano" / d / "table" for d in ("market", "research", "intelligence_validation")]

EXPECTED_ROUTES = {
    ("GET", "products"), ("POST", "products"),
    ("GET", "products/{product_id}"), ("PATCH", "products/{product_id}"),
    ("GET", "products/{product_id}/segments"), ("POST", "products/{product_id}/segments"),
    ("PATCH", "segments/{segment_id}"), ("DELETE", "segments/{segment_id}"),
    ("GET", "products/{product_id}/customers"), ("POST", "products/{product_id}/customers"),
    ("GET", "customers/{customer_id}"), ("PATCH", "customers/{customer_id}"), ("DELETE", "customers/{customer_id}"),
    ("GET", "customers/{customer_id}/interviews"), ("POST", "customers/{customer_id}/interviews"),
    ("GET", "interviews/{interview_id}"), ("PATCH", "interviews/{interview_id}"), ("DELETE", "interviews/{interview_id}"),
    ("GET", "products/{product_id}/survey-waves"), ("POST", "products/{product_id}/survey-waves"),
    ("GET", "survey-waves/{wave_id}"), ("PATCH", "survey-waves/{wave_id}"), ("DELETE", "survey-waves/{wave_id}"),
    ("POST", "survey-waves/{wave_id}/status"),
    ("GET", "survey-waves/{wave_id}/participations"), ("POST", "survey-waves/{wave_id}/participations"),
    ("PATCH", "participations/{participation_id}"), ("DELETE", "participations/{participation_id}"),
    ("GET", "survey-waves/{wave_id}/report"),
    ("GET", "products/{product_id}/insights"), ("POST", "products/{product_id}/insights"),
    ("GET", "insights/{insight_id}"), ("PATCH", "insights/{insight_id}"), ("DELETE", "insights/{insight_id}"),
    ("POST", "insights/{insight_id}/review-status"), ("POST", "insights/{insight_id}/evidence"),
    ("PATCH", "evidence/{evidence_id}"), ("DELETE", "evidence/{evidence_id}"),
    ("GET", "products/{product_id}/hypotheses"), ("POST", "insights/{insight_id}/hypotheses"),
    ("GET", "hypotheses/{hypothesis_id}"), ("PATCH", "hypotheses/{hypothesis_id}"), ("DELETE", "hypotheses/{hypothesis_id}"),
    ("POST", "hypotheses/{hypothesis_id}/experiments"),
    ("PATCH", "experiments/{experiment_id}"), ("DELETE", "experiments/{experiment_id}"),
    ("GET", "products/{product_id}/overview"), ("GET", "products/{product_id}/lookups"),
}

EXPECTED_FUNCTIONS = {
    "pmf/auth/require_owner",
    *(f"pmf/access/{n}" for n in ("product", "segment", "customer", "interview", "wave", "participation",
                                   "insight", "evidence", "hypothesis", "experiment")),
    "pmf/integrity/segment_in_product", "pmf/integrity/customer_in_product",
    "pmf/text/normalize", "pmf/text/is_blank", "pmf/util/patch_data",
    "pmf/lock/wave", "pmf/lock/insight",
    *(f"pmf/survey/{n}" for n in ("wave_state", "assert_wave_open", "assert_definition_unlocked",
                                   "validate_response", "participation_status")),
    *(f"pmf/report/{n}" for n in ("count_wave", "compute_pmf", "comparability", "build_wave_report")),
    "pmf/evidence/validate_source", "pmf/evidence/source_summary",
    "pmf/insight/count_valid_evidence", "pmf/insight/assert_reviewed",
    "pmf/validation/validate_experiment", "pmf/validation/validate_hypothesis_status",
    "pmf/guard/count_references",
}

ALWAYS_SENSITIVE = {"notes", "transcript", "existing_alternatives", "problem_context", "beneficiary_description",
                    "main_benefit", "improvement_request", "excerpt", "observed_result"}
SERVER_CONTROLLED = {"owner_user_id", "segment_id_snapshot", "created_at", "updated_at", "id"}

errors = []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def load_tables():
    tables = {"user": {"id", "created_at", "name", "email", "password"}}
    for d in TABLE_DIRS:
        for f in sorted(d.glob("*.xs")):
            s = f.read_text()
            name = re.search(r"^table (\w+)", s, re.M).group(1)
            schema = s[s.index("schema {"):s.index("index = [")]
            fields = set(re.findall(r"^\s{4}(?:int|text|timestamp|enum|email|decimal|bool|date|json|uuid)\??\s+(\w+)\??", schema, re.M))
            tables[name] = fields
    return tables


def input_block(s):
    m = re.search(r"\n  input \{\n(.*?)\n  \}\n", s, re.S)
    return m.group(1) if m else ""


def input_decls(block):
    """Yield (name, declaration_text_including_attribute_block)."""
    lines = block.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^\s{4}(?:[a-z]+\??(?:\[\])?\??)\s+(\w+)\??", line)
        if m:
            text = line
            if line.rstrip().endswith("{"):
                depth = line.count("{") - line.count("}")
                while depth > 0 and i + 1 < len(lines):
                    i += 1
                    text += "\n" + lines[i]
                    depth += lines[i].count("{") - lines[i].count("}")
            yield m.group(1), text
        i += 1


def check_db_refs(where, s, tables):
    evals = set(re.findall(r"eval = \{([^}]*)\}", s))
    eval_names = set()
    for e in evals:
        eval_names |= set(re.findall(r"(\w+)\s*:", e))
    for op, table in re.findall(r"\bdb\.(get|query|add|edit|patch|del|has) (\w+) \{", s):
        if table not in tables:
            err(where, f"db.{op} on unknown table '{table}'")
    for table, field in re.findall(r"\$db\.(\w+)\.(\w+)", s):
        if table not in tables:
            err(where, f"$db reference to unknown table '{table}'")
        elif field not in tables[table]:
            err(where, f"unknown field {table}.{field}")
    for table, body in re.findall(r"db\.add (\w+) \{\n\s*data = \{\n(.*?)\n\s*\}\n", s, re.S):
        for key in re.findall(r"^\s*(\w+)\s*:", body, re.M):
            if table in tables and key not in tables[table]:
                err(where, f"db.add {table} writes unknown field '{key}'")
    for m in re.finditer(r"db\.(?:get|query) (\w+) \{(.*?)\n\s{4,}\} as \$", s, re.S):
        table, body = m.group(1), m.group(2)
        out = re.search(r"output = \[([^\]]*)\]", body)
        if out and table in tables:
            for f in re.findall(r'"(\w+)"', out.group(1)):
                if f not in tables[table] and f not in eval_names:
                    err(where, f"output field '{f}' not in {table}")


def main():
    tables = load_tables()
    if len(tables) != 11:
        err("tables", f"expected 10 business tables + user, found {sorted(tables)}")

    # functions
    func_files = sorted((APP / "function").rglob("*.xs"))
    defined = {}
    for f in func_files:
        s = f.read_text()
        m = re.search(r'^function "([^"]+)"', s, re.M)
        if not m:
            err(f, "no function declaration")
            continue
        defined[m.group(1)] = f
        expected_path = APP / "function" / (m.group(1).split("/", 1)[1] + ".xs")
        if f != expected_path and f != APP / "function" / (m.group(1) + ".xs"):
            err(f, f"file path does not match function name {m.group(1)}")
    if set(defined) != EXPECTED_FUNCTIONS:
        err("functions", f"missing={sorted(EXPECTED_FUNCTIONS - set(defined))} extra={sorted(set(defined) - EXPECTED_FUNCTIONS)}")

    called = set()
    sources = {f: f.read_text() for f in (APP).rglob("*.xs")}
    for f, s in sources.items():
        rel = f.relative_to(ROOT)
        for target in re.findall(r'function\.run "([^"]+)"', s):
            called.add(target)
            if target not in defined:
                err(rel, f"function.run unknown target {target}")
        for bad, why in ((r"\bisolation\s*=", "transaction isolation is rejected by the validator"),
                         (r"db\.direct_query", "raw SQL is excluded (R3.3)"),
                         (r"db\.truncate|db\.bulk\.delete", "bulk destructive operation"),
                         (r"api_group\s*=\s*\"Authentication\"", "auth endpoints must not be modified (U10)"),
                         (r"\|set:[^|(\n]*\|set:", "chained |set: filters are ambiguous (greedy binding); use sequential var.update"),
                         (r"\|set:\"\w+\":[^()\n]*(==|!=|<=|>=| > | < )", "comparison inside a |set: argument must be parenthesized")):
            if re.search(bad, s):
                err(rel, why)
        for code in re.findall(r'error = "([^"]*)"', s):
            if not re.match(r"^[A-Z_]+: ", code):
                err(rel, f"error message lacks CODE prefix: {code[:40]}")
        check_db_refs(rel, s, tables)
    unused = set(defined) - called
    if unused:
        err("functions", f"defined but never called: {sorted(unused)}")

    # queries
    routes = {}
    query_files = sorted((APP / "api").rglob("*_*.xs"))
    for f in query_files:
        s = sources[f]
        rel = f.relative_to(ROOT)
        m = re.search(r'^query "([^"]+)" verb=(\w+) \{', s, re.M)
        if not m:
            continue
        route, verb = m.group(1), m.group(2)
        if (verb, route) in routes:
            err(rel, f"duplicate route {verb} {route}")
        routes[(verb, route)] = f
        if not re.search(r'^\s*api_group = "PMF App"$', s, re.M):
            err(rel, "api_group must be \"PMF App\"")
        if not re.search(r'^\s*auth = "user"$', s, re.M):
            err(rel, "auth must be \"user\"")
        stack = s[s.index("\n  stack {"):]
        first = re.search(r'function\.run "([^"]+)" \{\n\s*input = \{([^}]*)\}', stack)
        if not first or first.group(1) != "pmf/auth/require_owner" or "auth_id: $auth.id" not in first.group(2):
            err(rel, "first stack statement must be pmf/auth/require_owner with $auth.id")
        if (verb, route) != ("GET", "products") and (verb, route) != ("POST", "products") and \
                not re.search(r'function\.run "pmf/access/\w+"', stack):
            err(rel, "endpoint must load its target through a pmf/access/* loader")
        block = input_block(s)
        decls = dict(input_decls(block))
        for param in re.findall(r"\{(\w+)\}", route):
            if not re.search(rf"^\s{{4}}int {param}$", block, re.M):
                err(rel, f"route param {param} must be declared as required int")
        for name, text in decls.items():
            if name in ALWAYS_SENSITIVE and "sensitive = true" not in text:
                err(rel, f"input '{name}' must be sensitive = true")
            if name in SERVER_CONTROLLED:
                err(rel, f"server-controlled field '{name}' accepted as input")
            if name == "product_id" and "{product_id}" not in route:
                err(rel, "product_id accepted outside the route (client product authority)")
            if name == "review_status" and not (route.endswith("/review-status") or verb == "GET"):
                err(rel, "review_status accepted outside the review transition endpoint")
            if name == "closed_at" and not route.endswith("/status"):
                err(rel, "closed_at accepted outside the wave status endpoint")
        if "per_page" in decls:
            if "per_page?=25" not in decls["per_page"] or "max:100" not in decls["per_page"]:
                err(rel, "per_page must default to 25 with max 100")
            if "page?=1" not in decls.get("page", ""):
                err(rel, "page must default to 1")

    if set(routes) != EXPECTED_ROUTES:
        err("inventory", f"missing={sorted(EXPECTED_ROUTES - set(routes))} extra={sorted(set(routes) - EXPECTED_ROUTES)}")

    # route collisions: wildcard vs literal at the same position for the same verb and depth
    by_verb = {}
    for verb, route in routes:
        by_verb.setdefault(verb, []).append(route.split("/"))
    for verb, paths in by_verb.items():
        for i, a in enumerate(paths):
            for b in paths[i + 1:]:
                if len(a) != len(b):
                    continue
                clash = all(x == y or x.startswith("{") or y.startswith("{") for x, y in zip(a, b))
                mixed = any((x.startswith("{")) != (y.startswith("{")) for x, y in zip(a, b))
                if clash and mixed:
                    err("routes", f"collision {verb} {'/'.join(a)} vs {'/'.join(b)}")

    groups = list((APP / "api").rglob("api_group.xs"))
    if len(groups) != 1 or 'canonical = "pmf-app"' not in groups[0].read_text():
        err("api_group", "exactly one api_group with canonical pmf-app expected")
    if (APP / "table").exists() or list(APP.rglob("table/*.xs")):
        err("app", "xano/app must not contain table definitions")
    if list(APP.rglob("authentication")):
        err("app", "xano/app must not contain authentication endpoints")

    print(f"tables: {len(tables) - 1} business + user")
    print(f"functions: {len(defined)} defined, {len(called & set(defined))} called")
    print(f"endpoints: {len(routes)} (expected {len(EXPECTED_ROUTES)})")
    if errors:
        print(f"\nFAIL: {len(errors)} issue(s)")
        for e in errors:
            print(" -", e)
        return 1
    print("\nPASS: all static checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
