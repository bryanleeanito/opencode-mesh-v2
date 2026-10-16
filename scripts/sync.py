#!/usr/bin/env python3
"""sync.py — Sinkronisasi state antar mesin via git.

Usage:
    python3 sync.py --pull
    python3 sync.py --push
    python3 sync.py --status
"""
import argparse, json, os, subprocess, sys
from datetime import datetime

STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "state"))

def git_pull():
    print("[*] Pulling updates...")
    try:
        r = subprocess.run(["git", "pull", "--rebase"], capture_output=True, text=True)
        if r.returncode == 0:
            print("[+] Pull successful")
            return True
        else:
            print(f"[-] Pull failed: {r.stderr}")
            return False
    except Exception as e:
        print(f"[-] Error: {e}")
        return False

def git_push():
    print("[*] Pushing updates...")
    try:
        subprocess.run(["git", "add", "-A"], check=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subprocess.run(["git", "commit", "-m", f"mesh-sync: {timestamp}"], check=True)
        r = subprocess.run(["git", "push"], capture_output=True, text=True)
        if r.returncode == 0:
            print("[+] Push successful")
            return True
        else:
            print(f"[-] Push failed: {r.stderr}")
            return False
    except Exception as e:
        print(f"[-] Error: {e}")
        return False

def show_status():
    print("[*] Mesh sync status")
    print()
    for f in ["registry.json", "tasks.json", "findings.json", "ideas.json", "broadcasts.json", "handoffs.json", "subscriptions.json"]:
        path = os.path.join(STATE_DIR, f)
        if os.path.exists(path):
            with open(path) as fh:
                data = json.load(fh)
            count = len(data) if isinstance(data, (list, dict)) else 0
            print(f"  {f:25} {count} entries")
        else:
            print(f"  {f:25} -")
    print()
    try:
        r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
        if r.stdout.strip():
            print("[*] Git changes:")
            for line in r.stdout.strip().split("\n"):
                print(f"  {line}")
        else:
            print("[*] Git: clean")
    except:
        pass

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "--pull":
        git_pull()
    elif cmd == "--push":
        git_push()
    elif cmd == "--status":
        show_status()
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
