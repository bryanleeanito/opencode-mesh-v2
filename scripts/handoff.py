#!/usr/bin/env python3
"""handoff.py — Alihkan task dari satu mesin ke mesin lain.

Usage:
    python3 handoff.py --to tablet-analysis --task "analisa findings SQLi"
    python3 handoff.py --list
    python3 handoff.py --accept <id>
    python3 handoff.py --status <id>
"""
import argparse, json, os, sys
from datetime import datetime

STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "state"))

def load_handoffs():
    path = os.path.join(STATE_DIR, "handoffs.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []

def save_handoffs(handoffs):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "handoffs.json"), "w") as f:
        json.dump(handoffs, f, indent=2)

def handoff(to, task, priority="normal"):
    handoffs = load_handoffs()
    h_id = f"H-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    entry = {
        "id": h_id,
        "to": to,
        "task": task,
        "priority": priority,
        "status": "pending",
        "from": os.uname().nodename,
        "created": datetime.now().isoformat(),
    }
    handoffs.append(entry)
    save_handoffs(handoffs)
    print(f"[+] Handoff {h_id} -> {to}: {task}")
    print(f"    Status: pending")

def list_handoffs(filter_status=None):
    handoffs = load_handoffs()
    if filter_status:
        handoffs = [h for h in handoffs if h["status"] == filter_status]
    print(f"[*] Handoffs ({len(handoffs)} total)")
    print()
    for h in handoffs:
        print(f"  [{h['id']}] {h['to']:20} {h['status']:10} {h['task'][:50]}")
        print(f"      from {h['from']} at {h['created'][:19]}")

def update_status(h_id, status):
    handoffs = load_handoffs()
    for h in handoffs:
        if h["id"] == h_id:
            h["status"] = status
            h["updated"] = datetime.now().isoformat()
            save_handoffs(handoffs)
            print(f"[+] {h_id} -> {status}")
            return
    print(f"[-] Handoff {h_id} not found")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "--to":
        if len(args) < 4:
            print("Usage: handoff.py --to <mesin> --task <task>")
            return
        to = args[1]
        task_idx = args.index("--task")
        task = " ".join(args[task_idx + 1:])
        handoff(to, task)
    elif args[0] == "--list":
        status = None
        if "--status" in args:
            status = args[args.index("--status") + 1]
        list_handoffs(status)
    elif args[0] == "--accept":
        if len(args) < 2:
            print("Usage: handoff.py --accept <id>")
            return
        update_status(args[1], "accepted")
    elif args[0] == "--status":
        if len(args) < 3:
            print("Usage: handoff.py --status <id> <status>")
            return
        update_status(args[1], args[2])
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
