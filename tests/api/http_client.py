"""Guarded JSON client for the PMF API test suite.

- Requests may only target the configured host and known API paths (48 business routes + auth/me).
- The live host is refused unless the client was built with allow_live=True, which only the explicitly
  authorized live-workspace mode (live_target.py, --target live-pmf + confirmation phrase) does.
- Redirects are never followed (a 3xx could otherwise move a write to another host).
- Every response body is recorded for leakage checks (S06/S07); every request is logged for gate tests.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from safety import LIVE_HOSTS, UnsafeEnvironment


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise UnsafeEnvironment(f"redirect ({code}) refused; tests never follow redirects")


_OPENER = urllib.request.build_opener(NoRedirect)


def urllib_transport(method, url, headers, data):
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with _OPENER.open(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code < 400:
            raise UnsafeEnvironment(f"redirect ({exc.code}) refused") from None
        return exc.code, exc.read()


def route_regex(template):
    return re.compile("^" + re.escape(template).replace(re.escape("{id}"), r"\d+") + "$")


class Response:
    def __init__(self, status, body):
        self.status = status
        self.body = body

    @property
    def code(self):
        message = self.body.get("message", "") if isinstance(self.body, dict) else ""
        return message.split(":", 1)[0] if ":" in message else message

    def __repr__(self):
        return f"<{self.status} {json.dumps(self.body)[:300]}>"


class Api:
    def __init__(self, base, token, recorder, allowed_routes, transport, log, allowed_host, allow_live=False, ledger=None):
        self.base = base.rstrip("/")
        self.token = token
        self.recorder = recorder
        self.allowed = [(verb, route_regex(t)) for verb, t in allowed_routes]
        self.transport = transport
        self.log = log
        self.allowed_host = allowed_host
        self.allow_live = allow_live
        self.ledger = ledger

    def call(self, method, path, body=None, params=None):
        if not any(verb == method and rx.match(path) for verb, rx in self.allowed):
            raise UnsafeEnvironment(f"request outside the API inventory refused: {method} {path}")
        url = f"{self.base}/{path}"
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if (host in LIVE_HOSTS and not self.allow_live) or host != self.allowed_host:
            raise UnsafeEnvironment(f"request to unexpected host refused: {host}")
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        data = json.dumps(body).encode() if body is not None and method != "GET" else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.log.append((method, path, bool(self.token), self.token))
        status, raw = self.transport(method, url, headers, data)
        try:
            parsed = json.loads((raw or b"").decode() or "null")
        except ValueError:
            parsed = {"raw": raw.decode(errors="replace")[:500]}
        self.recorder.append(parsed)
        if self.ledger is not None:
            self.ledger.record(method, path, status, parsed)
        return Response(status, parsed)
