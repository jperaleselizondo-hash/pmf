"""Explicitly authorized synthetic testing in the EXISTING PMF workspace (owner decision, Phase 3).

Target is fixed: instance xgjc-aodb-3a7q, workspace `pmf` (ID 2), branch v1, API group canonical `pmf-app`.
Nothing here can reach another workspace (e.g. Goodz): every CLI call pins `-p pmf -w 2`, every Metadata API
path is pinned to /workspace/2/table…, and business/auth base URLs are fixed constants.

The Metadata API token (PMF_XANO_META_TOKEN) is read from the environment only. It needs
"Workspace Content: Read" (and "Workspace Content: Delete" for cleanup); it is never logged or stored.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import urllib.parse

from safety import SYNTHETIC_EMAIL_DOMAIN, SYNTHETIC_PRODUCT_PREFIX, UnsafeEnvironment

LIVE_INSTANCE = "xgjc-aodb-3a7q"
LIVE_HOST = "xgjc-aodb-3a7q.n7e.xano.io"
WORKSPACE_ID = 2
WORKSPACE_NAME = "pmf"
PROFILE = "pmf"
BRANCH = "v1"
BUSINESS_CANONICAL = "pmf-app"
AUTH_CANONICAL = "xHMmrw_d"  # observed Authentication group canonical in workspace 2
BASE_URL = f"https://{LIVE_HOST}/api:{BUSINESS_CANONICAL}"
AUTH_URL = f"https://{LIVE_HOST}/api:{AUTH_CANONICAL}"
META_URL = f"https://{LIVE_HOST}/api:meta"
CONFIRM_PHRASE = f"synthetic-tests:{LIVE_INSTANCE}:workspace-{WORKSPACE_ID}:{BUSINESS_CANONICAL}"
CLEANUP_PHRASE = f"delete-synthetic:{LIVE_INSTANCE}:workspace-{WORKSPACE_ID}"
# Children first: the order in which synthetic rows are deleted.
BUSINESS_TABLES = [
    "experiments", "hypotheses", "insight_evidence", "insights", "survey_participations",
    "survey_waves", "interviews", "customers", "segments", "products",
]
CLI = ["xano"]


def check_live_config(env, confirm_live):
    """Pure checks for the authorized live-workspace mode. Returns the expected owner id."""
    if confirm_live != CONFIRM_PHRASE:
        raise UnsafeEnvironment(f"live-workspace testing requires --confirm-live {CONFIRM_PHRASE}")
    if env.get("PMF_TEST_BASE_URL") != BASE_URL:
        raise UnsafeEnvironment(f"PMF_TEST_BASE_URL must be exactly {BASE_URL}")
    if env.get("PMF_TEST_AUTH_URL") != AUTH_URL:
        raise UnsafeEnvironment(f"PMF_TEST_AUTH_URL must be exactly {AUTH_URL}")
    for name in ("PMF_TEST_OWNER_TOKEN", "PMF_TEST_INTRUDER_TOKEN", "PMF_XANO_META_TOKEN", "PMF_TEST_OWNER_ID"):
        if not env.get(name):
            raise UnsafeEnvironment(f"{name} is not set")
    if env["PMF_TEST_OWNER_TOKEN"] == env["PMF_TEST_INTRUDER_TOKEN"]:
        raise UnsafeEnvironment("owner and intruder tokens must differ")
    if not re.fullmatch(r"[1-9][0-9]{0,12}", env["PMF_TEST_OWNER_ID"]):
        raise UnsafeEnvironment("PMF_TEST_OWNER_ID must be the owner's numeric user id")
    return int(env["PMF_TEST_OWNER_ID"])


def _cli_json(args, runner):
    try:
        proc = runner(CLI + args, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise UnsafeEnvironment(f"xano CLI unavailable: {type(exc).__name__}") from None
    if proc.returncode != 0:
        raise UnsafeEnvironment(f"xano {' '.join(args[:2])} failed")
    try:
        return json.loads(proc.stdout)
    except ValueError:
        raise UnsafeEnvironment(f"xano {' '.join(args[:2])} returned invalid JSON") from None


def verify_cli_identity(runner=subprocess.run):
    """Read-only: the pmf profile points at the expected instance and workspace 2 is `pmf`."""
    me = _cli_json(["profile", "me", "-p", PROFILE, "-o", "json"], runner)
    instance = ((me.get("extras") or {}).get("instance") or {}).get("name")
    if instance != LIVE_INSTANCE:
        raise UnsafeEnvironment("CLI profile `pmf` does not point at the expected instance")
    ws = _cli_json(["workspace", "get", "-p", PROFILE, "-w", str(WORKSPACE_ID), "-o", "json"], runner)
    if ws.get("id") != WORKSPACE_ID or ws.get("name") != WORKSPACE_NAME:
        raise UnsafeEnvironment("workspace 2 is not `pmf`")
    return ws


def verify_canonicals(runner=subprocess.run, require_business=True):
    """Read-only pull of workspace 2 / v1 (no --env, no --records) into a temp dir; checks API group canonicals."""
    tmp = tempfile.mkdtemp(prefix="pmf-canon-")
    try:
        args = ["workspace", "pull", "-p", PROFILE, "-w", str(WORKSPACE_ID), "-b", BRANCH, "-d", tmp]
        try:
            proc = runner(CLI + args, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.SubprocessError) as exc:
            raise UnsafeEnvironment(f"xano CLI unavailable: {type(exc).__name__}") from None
        if proc.returncode != 0:
            raise UnsafeEnvironment("read-only workspace pull failed")
        groups = {}
        for f in pathlib.Path(tmp, "api").rglob("*.xs"):
            text = f.read_text()
            m = re.search(r'^api_group "?([^"{]+?)"? \{', text, re.M)
            c = re.search(r'^\s*canonical = "([^"]+)"', text, re.M)
            if m and c:
                groups[m.group(1).strip()] = c.group(1)
        if groups.get("Authentication") != AUTH_CANONICAL:
            raise UnsafeEnvironment("Authentication canonical in workspace 2 is not the expected one")
        business = [name for name, canon in groups.items() if canon == BUSINESS_CANONICAL]
        if require_business and business != ["PMF App"]:
            raise UnsafeEnvironment("API group `PMF App` with canonical pmf-app is not deployed in workspace 2")
        return groups
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class MetaClient:
    """Metadata API client pinned to workspace 2 table/content paths. DELETE only on approved table ids."""

    PATH_RE = re.compile(rf"^/workspace/{WORKSPACE_ID}/table(?:/(\d+)/content(?:/(\d+))?)?$")

    def __init__(self, token, transport):
        self.token = token
        self.transport = transport
        self.table_ids = {}
        self.deletable_tables = set()

    def _call(self, method, path, params=None):
        m = self.PATH_RE.match(path)
        if not m:
            raise UnsafeEnvironment(f"metadata path refused: {path}")
        table_id, row_id = m.group(1), m.group(2)
        if method == "DELETE":
            if not row_id or int(table_id) not in self.deletable_tables:
                raise UnsafeEnvironment(f"metadata delete refused: {path}")
        elif method != "GET" or row_id:
            raise UnsafeEnvironment(f"metadata {method} refused: {path}")
        url = META_URL + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json", "x-data-source": "live"}
        status, raw = self.transport(method, url, headers, None)
        if status != 200:
            raise UnsafeEnvironment(f"metadata {method} {path} returned {status}")
        return json.loads((raw or b"null").decode() or "null")

    def resolve_tables(self):
        listing = self._call("GET", f"/workspace/{WORKSPACE_ID}/table", {"page": 1, "per_page": 500})
        items = listing.get("items", listing) if isinstance(listing, dict) else listing
        found = {}
        for t in items:
            found.setdefault(t.get("name"), []).append(t.get("id"))
        for name in BUSINESS_TABLES + ["user"]:
            if len(found.get(name, [])) != 1:
                raise UnsafeEnvironment(f"table `{name}` not found exactly once in workspace 2")
            self.table_ids[name] = found[name][0]
        return dict(self.table_ids)

    def count(self, name):
        if name not in BUSINESS_TABLES:
            raise UnsafeEnvironment(f"row counts are limited to business tables (got {name})")
        page = self._call("GET", f"/workspace/{WORKSPACE_ID}/table/{self.table_ids[name]}/content", {"page": 1, "per_page": 1})
        return int(page.get("itemsTotal", 0))

    def counts(self):
        return {name: self.count(name) for name in BUSINESS_TABLES}

    def rows(self, name):
        if name not in BUSINESS_TABLES:
            raise UnsafeEnvironment(f"row reads are limited to business tables (got {name})")
        out, page = [], 1
        while True:
            data = self._call("GET", f"/workspace/{WORKSPACE_ID}/table/{self.table_ids[name]}/content", {"page": page, "per_page": 500})
            items = data.get("items") or []
            out.extend(items if isinstance(items, list) else [])
            if not data.get("nextPage"):
                return out
            page = data["nextPage"]

    def delete(self, name, row_id):
        return self._call("DELETE", f"/workspace/{WORKSPACE_ID}/table/{self.table_ids[name]}/content/{int(row_id)}")


def verify_synthetic(rows, owner_id):
    """Pure: every row in the ten business tables must belong to a SYNTH- product of the owner.

    Returns (problems, plan) where plan maps table -> sorted ids to delete. Any problem means STOP.
    """
    problems = []
    ids = {name: {r.get("id") for r in rows.get(name, [])} for name in BUSINESS_TABLES}
    for r in rows.get("products", []):
        if not str(r.get("name") or "").startswith(SYNTHETIC_PRODUCT_PREFIX):
            problems.append(f"products#{r.get('id')}: not a synthetic product name")
        if r.get("owner_user_id") != owner_id:
            problems.append(f"products#{r.get('id')}: not owned by the designated owner")
    products = ids["products"]

    def need(table, row, field, parents, optional=False):
        value = row.get(field)
        if value is None and optional:
            return
        if value not in parents:
            problems.append(f"{table}#{row.get('id')}: {field}={value} is not a synthetic parent")

    for r in rows.get("segments", []):
        need("segments", r, "product_id", products)
    for r in rows.get("customers", []):
        need("customers", r, "product_id", products)
        need("customers", r, "segment_id", ids["segments"], optional=True)
        email = r.get("email")
        if email is not None and not str(email).lower().endswith(SYNTHETIC_EMAIL_DOMAIN):
            problems.append(f"customers#{r.get('id')}: non-synthetic email")
        name = r.get("name")
        if name is not None and not str(name).startswith("SYNTH"):
            problems.append(f"customers#{r.get('id')}: non-synthetic name")
    for r in rows.get("interviews", []):
        need("interviews", r, "customer_id", ids["customers"])
    for r in rows.get("survey_waves", []):
        need("survey_waves", r, "product_id", products)
    for r in rows.get("survey_participations", []):
        need("survey_participations", r, "survey_wave_id", ids["survey_waves"])
        need("survey_participations", r, "customer_id", ids["customers"])
    for r in rows.get("insights", []):
        need("insights", r, "product_id", products)
    for r in rows.get("insight_evidence", []):
        need("insight_evidence", r, "insight_id", ids["insights"])
        need("insight_evidence", r, "interview_id", ids["interviews"], optional=True)
        need("insight_evidence", r, "survey_participation_id", ids["survey_participations"], optional=True)
    for r in rows.get("hypotheses", []):
        need("hypotheses", r, "insight_id", ids["insights"])
    for r in rows.get("experiments", []):
        need("experiments", r, "hypothesis_id", ids["hypotheses"])
    plan = {name: sorted(i for i in ids[name] if i is not None) for name in BUSINESS_TABLES}
    return problems, plan


def default_ledger_path(tag):
    root = pathlib.Path(os.environ.get("PMF_TEST_LEDGER_DIR", pathlib.Path.home() / ".pmf-test-runs"))
    return root / f"run-{tag}.jsonl"


LEDGER_ROUTES = [
    (re.compile(r"^products$"), "products", lambda b: [b.get("id")]),
    (re.compile(r"^products/\d+/segments$"), "segments", lambda b: [b.get("id")]),
    (re.compile(r"^products/\d+/customers$"), "customers", lambda b: [b.get("id")]),
    (re.compile(r"^customers/\d+/interviews$"), "interviews", lambda b: [b.get("id")]),
    (re.compile(r"^products/\d+/survey-waves$"), "survey_waves", lambda b: [b.get("id")]),
    (re.compile(r"^survey-waves/\d+/participations$"), "survey_participations", lambda b: [p.get("id") for p in b.get("created", [])]),
    (re.compile(r"^products/\d+/insights$"), "insights", lambda b: [b.get("id")]),
    (re.compile(r"^insights/\d+/evidence$"), "insight_evidence", lambda b: [(b.get("evidence") or {}).get("id")]),
    (re.compile(r"^insights/\d+/hypotheses$"), "hypotheses", lambda b: [b.get("id")]),
    (re.compile(r"^hypotheses/\d+/experiments$"), "experiments", lambda b: [b.get("id")]),
]


class Ledger:
    """Append-only JSONL of created synthetic record ids (no tokens, no content), flushed per write."""

    def __init__(self, path, tag):
        self.path = pathlib.Path(path)
        self.tag = tag
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, method, path, status, body):
        if method != "POST" or status != 200 or not isinstance(body, dict):
            return
        for rx, table, extract in LEDGER_ROUTES:
            if rx.match(path):
                for row_id in extract(body):
                    if row_id is not None:
                        with self.path.open("a") as fh:
                            fh.write(json.dumps({"run": self.tag, "table": table, "id": row_id}) + "\n")
                return


def check_live_canary(owner_me, intruder_me, products, owner_id):
    """Read-only canary for the live workspace: the real designated owner plus one synthetic non-owner."""
    if not isinstance(owner_me, dict) or owner_me.get("id") != owner_id:
        raise UnsafeEnvironment("owner token does not belong to PMF_TEST_OWNER_ID")
    email = str((intruder_me or {}).get("email") or "").lower()
    if not email.endswith(SYNTHETIC_EMAIL_DOMAIN) or (intruder_me or {}).get("id") in (None, owner_id):
        raise UnsafeEnvironment("intruder must be a distinct synthetic @pmf-test.invalid account")
    if not isinstance(products, dict) or products.get("items") != []:
        raise UnsafeEnvironment("the owner already has products; live synthetic testing requires empty business tables")
    return True


def require_empty(meta, stage):
    counts = meta.counts()
    non_empty = {k: v for k, v in counts.items() if v}
    if non_empty:
        raise UnsafeEnvironment(f"business tables not empty {stage}: {non_empty}")
    return counts
