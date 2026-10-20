#!/usr/bin/env python3
"""delegate.py — Delegasi task ke mesin lain (dynamic).

Usage:
    python3 delegate.py --to kali-attack --task "bypass WAF target.com"
    python3 delegate.py --to all --task "laporan mingguan"
    python3 delegate.py --list
    python3 delegate.py --status <id> <status>
"""
import argparse, json, os, platform, sys
from datetime import datetime

STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "state"))

def load_tasks():
    path = os.path.join(STATE_DIR, "tasks.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "tasks.json"), "w") as f:
        json.dump(tasks, f, indent=2)

def delegate(to, task, priority="normal"):
    tasks = load_tasks()
    t_id = f"T-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    entry = {
        "id": t_id,
        "to": to,
        "task": task,
        "priority": priority,
        "status": "pending",
        "created": datetime.now().isoformat(),
        "from": platform.node(),
    }
    tasks.append(entry)
    save_tasks(tasks)
    print(f"[+] Task {t_id} -> {to}: {task}")
    print(f"    Status: pending")

def list_tasks(filter_status=None):
    tasks = load_tasks()
    if filter_status:
        tasks = [t for t in tasks if t["status"] == filter_status]
    print(f"[*] Tasks ({len(tasks)} total)")
    print()
    for t in tasks:
        print(f"  [{t['id']}] {t['to']:20} {t['status']:10} {t['task'][:50]}")

def update_status(task_id, status):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = status
            t["updated"] = datetime.now().isoformat()
            save_tasks(tasks)
            print(f"[+] {task_id} -> {status}")
            return
    print(f"[-] Task {task_id} not found")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "--to":
        if len(args) < 4:
            print("Usage: delegate.py --to <mesin> --task <task>")
            return
        to = args[1]
        task_idx = args.index("--task")
        task = " ".join(args[task_idx + 1:])
        delegate(to, task)
    elif args[0] == "--list":
        status = None
        if "--status" in args:
            status = args[args.index("--status") + 1]
        list_tasks(status)
    elif args[0] == "--status":
        if len(args) < 3:
            print("Usage: delegate.py --status <id> <status>")
            return
        update_status(args[1], args[2])
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
