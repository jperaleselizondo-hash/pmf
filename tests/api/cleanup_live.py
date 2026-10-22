#!/usr/bin/env python3
"""Controlled cleanup of synthetic test data in the PMF workspace (xgjc-aodb-3a7q, workspace 2).

Default is a DRY RUN. Nothing is deleted unless --execute is given with the exact confirmation phrase.

Procedure:
  1. Verify the CLI target (instance, workspace 2 = pmf) and resolve the ten business tables + `user`.
  2. Read every row of the ten business tables (content is never printed).
  3. Verify ALL rows are synthetic: every product starts with SYNTH- and belongs to PMF_TEST_OWNER_ID,
     every other row chains to those products, customer emails/names are synthetic. Any doubt → STOP.
  4. Optional --ledger: report rows that this run's ledger did not record (still synthetic, from older runs).
  5. --execute: re-count all ten tables (must equal the verified plan, else STOP), then delete the verified
     row ids table by table, children first (never truncate). Each DELETE must return 200/204 AND a
     follow-up read must return 404; anything else stops with exit 4.
  6. --remove-test-user: delete exactly one `user` row — the id returned by the intruder token's auth/me,
     only if its email ends with @pmf-test.invalid and it is not PMF_TEST_OWNER_ID.
  7. Verify the ten business tables contain zero rows.

Environment (never commit): PMF_XANO_META_TOKEN (Workspace Content Read + Delete), PMF_TEST_OWNER_ID,
PMF_TEST_INTRUDER_TOKEN (only with --remove-test-user).

Exit codes: 0 ok · 2 unsafe/unverifiable (nothing deleted) · 4 deletion incomplete or tables not empty.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_target as live  # noqa: E402
from http_client import Api, urllib_transport  # noqa: E402
from safety import SYNTHETIC_EMAIL_DOMAIN, UnsafeEnvironment  # noqa: E402


def read_ledger(path):
    found = {}
    with open(path) as fh:
        for line in fh:
            entry = json.loads(line)
            found.setdefault(entry["table"], set()).add(entry["id"])
    return found


def verified_test_user(env, owner_id, transport):
    token = env.get("PMF_TEST_INTRUDER_TOKEN")
    if not token:
        raise UnsafeEnvironment("PMF_TEST_INTRUDER_TOKEN is required to identify the test user")
    api = Api(live.AUTH_URL, token, [], [("GET", "auth/me")], transport, [], live.LIVE_HOST, allow_live=True)
    me = api.call("GET", "auth/me")
    email = str((me.body or {}).get("email") or "").lower() if me.status == 200 else ""
    user_id = (me.body or {}).get("id") if me.status == 200 else None
    if not email.endswith(SYNTHETIC_EMAIL_DOMAIN) or user_id in (None, owner_id):
        raise UnsafeEnvironment("the test user is not a distinct synthetic @pmf-test.invalid account")
    return user_id


def run_cleanup(env, confirm, *, execute=False, remove_test_user=False, ledger_path=None,
                cli_runner=subprocess.run, meta=None, transport=urllib_transport, out=print):
    try:
        if confirm != live.CLEANUP_PHRASE:
            raise UnsafeEnvironment(f"cleanup requires --confirm-cleanup {live.CLEANUP_PHRASE}")
        for name in ("PMF_XANO_META_TOKEN", "PMF_TEST_OWNER_ID"):
            if not env.get(name):
                raise UnsafeEnvironment(f"{name} is not set")
        owner_id = int(env["PMF_TEST_OWNER_ID"])
        live.verify_cli_identity(cli_runner)
        meta = meta or live.MetaClient(env["PMF_XANO_META_TOKEN"], transport)
        meta.resolve_tables()
        rows = {name: meta.rows(name) for name in live.BUSINESS_TABLES}
        problems, plan = live.verify_synthetic(rows, owner_id)
        if problems:
            out(f"STOP: {len(problems)} row(s) could not be verified as synthetic; nothing deleted")
            for p in problems[:20]:
                out(f"  - {p}")
            return 2
        test_user = verified_test_user(env, owner_id, transport) if remove_test_user else None
    except UnsafeEnvironment as exc:
        out(f"STOP: {exc}; nothing deleted")
        return 2

    if ledger_path:
        ledger = read_ledger(ledger_path)
        unlisted = {t: sorted(set(ids) - ledger.get(t, set())) for t, ids in plan.items()}
        unlisted = {t: ids for t, ids in unlisted.items() if ids}
        out(f"LEDGER rows not recorded by this ledger (synthetic, older runs): {unlisted or 'none'}")
    out("PLAN " + ", ".join(f"{t}={len(ids)}" for t, ids in plan.items()) + (f", user=1 (id {test_user})" if test_user else ""))
    if not execute:
        out("DRY RUN: nothing deleted (add --execute to delete exactly these rows)")
        return 0

    try:
        recount = meta.counts()
    except UnsafeEnvironment as exc:
        out(f"STOP: {exc}; nothing deleted")
        return 2
    changed = {t: (len(plan[t]), recount[t]) for t in live.BUSINESS_TABLES if recount[t] != len(plan[t])}
    if changed:
        out(f"STOP: table contents changed since verification {changed}; nothing deleted")
        return 2

    try:
        for name in live.BUSINESS_TABLES:
            meta.deletable_tables = {meta.table_ids[name]}
            for row_id in plan[name]:
                meta.delete(name, row_id)  # confirmed by a follow-up 404
            out(f"deleted {len(plan[name])} {name}")
        if test_user is not None:
            meta.deletable_tables = {meta.table_ids["user"]}
            meta.delete("user", test_user)
            out(f"deleted test user {test_user}")
    except UnsafeEnvironment as exc:
        out(f"INCOMPLETE: deletion stopped: {exc}. Rerun the dry run before anything else; never truncate.")
        return 4
    finally:
        meta.deletable_tables = set()

    try:
        counts = meta.counts()
    except UnsafeEnvironment as exc:
        out(f"INCOMPLETE: final verification failed: {exc}")
        return 4
    remaining = {k: v for k, v in counts.items() if v}
    if remaining:
        out(f"INCOMPLETE: business tables not empty after cleanup: {remaining} (investigate; do not truncate)")
        return 4
    out("VERIFIED: all ten business tables contain zero records")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm-cleanup", required=True, help=f"must be exactly {live.CLEANUP_PHRASE}")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--remove-test-user", action="store_true")
    parser.add_argument("--ledger")
    args = parser.parse_args()
    return run_cleanup(os.environ, args.confirm_cleanup, execute=args.execute,
                       remove_test_user=args.remove_test_user, ledger_path=args.ledger)


if __name__ == "__main__":
    sys.exit(main())
