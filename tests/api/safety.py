"""Environment safety guard for the PMF API test suite (docs/API_V1_PROPOSAL.md, Appendix R8.5).

No request with a write verb may reach any server unless the target is POSITIVELY identified as the
selected isolated ephemeral tenant, using authoritative Xano Metadata API data (read via the CLI), and a
read-only canary proves the environment holds only synthetic identities and data. The live host is
hard-denied; these rules must never be relaxed to make a test run.
"""
import datetime
import json
import re
import subprocess
import time
import urllib.parse

LIVE_HOSTS = frozenset({"xgjc-aodb-3a7q.n7e.xano.io"})
XANO_PROFILE = "pmf"
XANO_WORKSPACE_ID = "2"
SYNTHETIC_EMAIL_DOMAIN = "@pmf-test.invalid"
SYNTHETIC_PRODUCT_PREFIX = "SYNTH-"
TENANT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,62}$")
# Xano URL form: <host>/api:<canonical>[:<branch>] (xanoscript_docs/apis.md). Tenant-specific prefixes
# are not documented, so anything else (extra path segments, other canonicals) is rejected.
BUSINESS_PATH_RE = re.compile(r"^/api:pmf-app(?::(?P<branch>[A-Za-z0-9._-]+))?/?$")
AUTH_PATH_RE = re.compile(r"^/api:(?P<canonical>[A-Za-z0-9_-]+)(?::(?P<branch>[A-Za-z0-9._-]+))?/?$")
BAD_TENANT_STATES = ("delet", "fail", "error", "expire", "suspend", "stop")


class UnsafeEnvironment(Exception):
    """Raised when the configured target is not a positively identified isolated environment."""


def check_config(base_url, auth_url, tenant_name, confirm_tenant, owner_token, intruder_token):
    """Pure configuration checks (no network). Returns {"host", "branch", "auth_canonical"}."""
    for label, value in (("PMF_TEST_BASE_URL", base_url), ("PMF_TEST_AUTH_URL", auth_url),
                         ("PMF_TEST_TENANT_NAME", tenant_name), ("PMF_TEST_OWNER_TOKEN", owner_token),
                         ("PMF_TEST_INTRUDER_TOKEN", intruder_token)):
        if not value:
            raise UnsafeEnvironment(f"{label} is not set")
    if not TENANT_NAME_RE.match(tenant_name):
        raise UnsafeEnvironment("PMF_TEST_TENANT_NAME has an unexpected format")
    if confirm_tenant != tenant_name:
        raise UnsafeEnvironment("--confirm-tenant does not match PMF_TEST_TENANT_NAME")

    base = urllib.parse.urlsplit(base_url)
    auth = urllib.parse.urlsplit(auth_url)
    for label, parts in (("base", base), ("auth", auth)):
        if parts.scheme != "https":
            raise UnsafeEnvironment(f"{label} URL must use https")
        if parts.username or parts.password or parts.port not in (None, 443) or parts.query or parts.fragment:
            raise UnsafeEnvironment(f"{label} URL must not contain credentials, ports, query or fragment")
    host = (base.hostname or "").lower()
    if host in LIVE_HOSTS or (auth.hostname or "").lower() in LIVE_HOSTS:
        raise UnsafeEnvironment(f"refusing to run against the live host {host}")
    if (auth.hostname or "").lower() != host:
        raise UnsafeEnvironment("base and auth URLs must use the same host")
    business = BUSINESS_PATH_RE.match(base.path)
    if not business:
        raise UnsafeEnvironment("base URL path must be exactly /api:pmf-app or /api:pmf-app:<branch>")
    auth_match = AUTH_PATH_RE.match(auth.path)
    if not auth_match or auth_match.group("canonical") == "pmf-app":
        raise UnsafeEnvironment("auth URL path must be /api:<auth canonical>[:<branch>]")
    if business.group("branch") != auth_match.group("branch"):
        raise UnsafeEnvironment("base and auth URLs must target the same branch")
    if owner_token == intruder_token:
        raise UnsafeEnvironment("owner and intruder tokens must differ")
    return {"host": host, "branch": business.group("branch"), "auth_canonical": auth_match.group("canonical")}


def _expires_ms(raw):
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return raw * 1000 if raw < 1e12 else raw
    text = str(raw).strip().replace(" ", "T", 1)
    if re.match(r".*[+-]\d{4}$", text):
        text = text[:-2] + ":" + text[-2:]
    try:
        parsed = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.timestamp() * 1000


def check_tenant_metadata(meta, tenant_name, host, now_ms=None, min_remaining_ms=10 * 60_000):
    """Authoritative identity: the Metadata API record of the named ephemeral tenant must own the host."""
    if not isinstance(meta, dict):
        raise UnsafeEnvironment("tenant metadata is missing or malformed")
    if meta.get("name") != tenant_name:
        raise UnsafeEnvironment("tenant metadata name does not match PMF_TEST_TENANT_NAME")
    expires = _expires_ms(meta.get("ephemeral_expires_at"))
    if expires is None:
        raise UnsafeEnvironment("tenant is not an ephemeral tenant (no ephemeral_expires_at)")
    now_ms = now_ms if now_ms is not None else time.time() * 1000
    if expires - now_ms < min_remaining_ms:
        raise UnsafeEnvironment("ephemeral tenant has expired or expires within 10 minutes")
    state = str(meta.get("state") or "").lower()
    if any(bad in state for bad in BAD_TENANT_STATES):
        raise UnsafeEnvironment(f"tenant state '{state}' is not usable")
    allowed = {str(d).lower() for d in (meta.get("xano_domain"), meta.get("domain")) if d}
    if not meta.get("xano_domain"):
        raise UnsafeEnvironment("tenant metadata has no xano_domain")
    if allowed & LIVE_HOSTS:
        raise UnsafeEnvironment("tenant resolves to the live host; isolation cannot be established by host")
    if host not in allowed:
        raise UnsafeEnvironment("configured host is not a domain of the selected ephemeral tenant")
    return True


def fetch_tenant_metadata(tenant_name, runner=subprocess.run):
    """Read-only: `xano ephemeral get <name> -p pmf -w 2 -o json` (Metadata API through the CLI)."""
    cmd = ["xano", "ephemeral", "get", tenant_name, "-p", XANO_PROFILE, "-w", XANO_WORKSPACE_ID, "-o", "json"]
    try:
        proc = runner(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise UnsafeEnvironment(f"could not read tenant metadata: {type(exc).__name__}") from None
    if proc.returncode != 0:
        raise UnsafeEnvironment("tenant metadata lookup failed (does the ephemeral tenant exist in workspace 2?)")
    try:
        return json.loads(proc.stdout)
    except ValueError:
        raise UnsafeEnvironment("tenant metadata is not valid JSON") from None


def check_canary(owner_me, intruder_me, products):
    """Read-only canary results must prove the environment holds only synthetic identities and data."""
    for label, me in (("owner", owner_me), ("intruder", intruder_me)):
        email = str((me or {}).get("email") or "").lower()
        if not email.endswith(SYNTHETIC_EMAIL_DOMAIN):
            raise UnsafeEnvironment(f"{label} account is not a synthetic {SYNTHETIC_EMAIL_DOMAIN} identity")
        if (me or {}).get("id") is None:
            raise UnsafeEnvironment(f"{label} auth/me response has no id")
    if owner_me.get("id") == intruder_me.get("id"):
        raise UnsafeEnvironment("owner and intruder resolve to the same user")
    if not isinstance(products, dict) or not isinstance(products.get("items"), list):
        raise UnsafeEnvironment("product canary returned an unexpected shape")
    total = products.get("itemsTotal")
    if total is not None and total > len(products["items"]):
        raise UnsafeEnvironment("product canary is incomplete (more products than one page); refusing")
    for item in products["items"]:
        if not str(item.get("name", "")).startswith(SYNTHETIC_PRODUCT_PREFIX):
            raise UnsafeEnvironment("non-synthetic product found; aborting before any write")
    return True
