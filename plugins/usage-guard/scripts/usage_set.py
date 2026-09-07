#!/usr/bin/env python3
"""usage_set.py: write the status file the usage-guard hook reads.

Feed it from whatever you trust: the numbers shown by /usage, a monitoring script,
a scheduled job that polls your own billing dashboard. This tool stays local and
touches no credentials.

  python usage_set.py --session 42 --weekly 61 --session-reset 2026-09-07T10:00:00+00:00
  python usage_set.py --from-json snapshot.json     # same keys as the status file
  python usage_set.py --show
"""
import argparse
import datetime
import json
import os
import sys

HOME_DIR = os.path.join(os.path.expanduser("~"), ".claude", "usage-guard")
STATUS = os.environ.get("USAGE_GUARD_STATUS") or os.path.join(HOME_DIR, "status.json")
KEYS = ("session_pct", "weekly_pct", "session_reset_at", "weekly_reset_at", "account")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Write the usage-guard status file.")
    ap.add_argument("--session", type=float, help="session usage in percent")
    ap.add_argument("--weekly", type=float, help="weekly usage in percent")
    ap.add_argument("--session-reset", help="ISO timestamp of the session reset")
    ap.add_argument("--weekly-reset", help="ISO timestamp of the weekly reset")
    ap.add_argument("--account", help="label shown in the usage line")
    ap.add_argument("--from-json", help="read the values from a JSON file")
    ap.add_argument("--show", action="store_true", help="print the current status file")
    args = ap.parse_args(argv)

    if args.show:
        try:
            with open(STATUS, encoding="utf-8") as fh:
                print(fh.read())
        except OSError:
            print(f"no status file at {STATUS}")
        return 0

    status = {}
    try:
        with open(STATUS, encoding="utf-8") as fh:
            status = json.load(fh)
    except (OSError, ValueError):
        pass
    if args.from_json:
        with open(args.from_json, encoding="utf-8") as fh:
            status.update({k: v for k, v in json.load(fh).items() if k in KEYS})
    for key, val in (("session_pct", args.session), ("weekly_pct", args.weekly),
                     ("session_reset_at", args.session_reset), ("weekly_reset_at", args.weekly_reset),
                     ("account", args.account)):
        if val is not None:
            status[key] = val
    if "session_pct" not in status:
        ap.error("nothing to write: pass --session or --from-json")
    status["fetched_at"] = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    os.makedirs(os.path.dirname(STATUS), exist_ok=True)
    tmp = STATUS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(status, fh, indent=1)
    os.replace(tmp, STATUS)
    print(json.dumps({"ok": True, "status": STATUS, **{k: status.get(k) for k in KEYS}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
