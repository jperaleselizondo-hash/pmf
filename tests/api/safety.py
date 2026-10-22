"""Environment safety guard for the PMF API test suite (docs/API_V1_PROPOSAL.md, Appendix R8.5).

No write test may run unless every check passes. The live Xano host is hard-denied.
"""
import urllib.parse

LIVE_HOSTS = frozenset({"xgjc-aodb-3a7q.n7e.xano.io"})
SYNTHETIC_EMAIL_DOMAIN = "@pmf-test.invalid"
SYNTHETIC_PRODUCT_PREFIX = "SYNTH-"
API_PATH_PREFIX = "/api:pmf-app"


class UnsafeEnvironment(Exception):
    """Raised when the configured target is not a positively identified isolated environment."""


def check_config(base_url, auth_url, env_host, tenant_name, confirm_tenant, owner_token, intruder_token):
    """Pure configuration checks (no network). Returns the parsed base host."""
    for label, value in (("PMF_TEST_BASE_URL", base_url), ("PMF_TEST_AUTH_URL", auth_url),
                         ("PMF_TEST_ENV_HOST", env_host), ("PMF_TEST_TENANT_NAME", tenant_name),
                         ("PMF_TEST_OWNER_TOKEN", owner_token), ("PMF_TEST_INTRUDER_TOKEN", intruder_token)):
        if not value:
            raise UnsafeEnvironment(f"{label} is not set")

    base = urllib.parse.urlparse(base_url)
    auth = urllib.parse.urlparse(auth_url)
    if base.scheme != "https" or auth.scheme != "https":
        raise UnsafeEnvironment("base and auth URLs must use https")
    host = (base.hostname or "").lower()
    if host in LIVE_HOSTS or (auth.hostname or "").lower() in LIVE_HOSTS:
        raise UnsafeEnvironment(f"refusing to run against the live host {host}")
    if host != env_host.lower() or (auth.hostname or "").lower() != env_host.lower():
        raise UnsafeEnvironment("base/auth URL host does not match PMF_TEST_ENV_HOST (the isolated tenant host)")
    if not base.path.startswith(API_PATH_PREFIX):
        raise UnsafeEnvironment(f"base URL path must start with {API_PATH_PREFIX}")
    if confirm_tenant != tenant_name:
        raise UnsafeEnvironment("--confirm-tenant does not match PMF_TEST_TENANT_NAME")
    if owner_token == intruder_token:
        raise UnsafeEnvironment("owner and intruder tokens must differ")
    return host


def check_canary(owner_me, intruder_me, products):
    """Read-only canary results must prove the environment holds only synthetic identities and data."""
    for label, me in (("owner", owner_me), ("intruder", intruder_me)):
        email = (me or {}).get("email") or ""
        if not email.endswith(SYNTHETIC_EMAIL_DOMAIN):
            raise UnsafeEnvironment(f"{label} account is not a synthetic {SYNTHETIC_EMAIL_DOMAIN} identity")
    if (owner_me or {}).get("id") == (intruder_me or {}).get("id"):
        raise UnsafeEnvironment("owner and intruder resolve to the same user")
    for item in (products or {}).get("items", []):
        if not str(item.get("name", "")).startswith(SYNTHETIC_PRODUCT_PREFIX):
            raise UnsafeEnvironment("non-synthetic product found; aborting before any write")
    return True
