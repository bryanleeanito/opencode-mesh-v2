#!/usr/bin/env python3
"""share.py — Share findings ke mesin lain.

Usage:
    python3 share.py --type finding --message "SQLi di /login"
    python3 share.py --type clue --message "Target pakai Cloudflare"
    python3 share.py --list
"""
import argparse, json, os, sys
from datetime import datetime

STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "state"))

def load_findings():
    path = os.path.join(STATE_DIR, "findings.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []

def save_findings(findings):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "findings.json"), "w") as f:
        json.dump(findings, f, indent=2)

def share(f_type, message):
    findings = load_findings()
    f_id = f"F-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    entry = {
        "id": f_id,
        "type": f_type,
        "message": message,
        "author": os.uname().nodename,
        "created": datetime.now().isoformat(),
    }
    findings.append(entry)
    save_findings(findings)
    print(f"[+] {f_type.upper()} {f_id}: {message}")

def list_findings():
    findings = load_findings()
    print(f"[*] Findings ({len(findings)} total)")
    print()
    for f in findings:
        print(f"  [{f['id']}] [{f['type']:10}] {f['message']}")
        print(f"      by {f['author']} at {f['created'][:19]}")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "--type":
        if len(args) < 4:
            print("Usage: share.py --type <type> --message <message>")
            return
        f_type = args[1]
        msg_idx = args.index("--message")
        message = " ".join(args[msg_idx + 1:])
        share(f_type, message)
    elif args[0] == "--list":
        list_findings()
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
