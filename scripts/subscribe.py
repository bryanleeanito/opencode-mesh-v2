#!/usr/bin/env python3
"""subscribe.py — Follow topik di mesh network.

Usage:
    python3 subscribe.py --topic security
    python3 subscribe.py --list
    python3 subscribe.py --unsubscribe security
"""
import argparse, json, os, platform, sys
from datetime import datetime

STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "state"))

def load_subs():
    path = os.path.join(STATE_DIR, "subscriptions.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []

def save_subs(subs):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "subscriptions.json"), "w") as f:
        json.dump(subs, f, indent=2)

def subscribe(topic):
    subs = load_subs()
    # Remove old entry for this machine
    machine = platform.node()
    subs = [s for s in subs if s["machine"] != machine]
    subs.append({
        "machine": machine,
        "topic": topic,
        "created": datetime.now().isoformat(),
    })
    save_subs(subs)
    print(f"[+] Subscribed to: {topic}")

def unsubscribe(topic):
    subs = load_subs()
    machine = platform.node()
    subs = [s for s in subs if not (s["machine"] == machine and s["topic"] == topic)]
    save_subs(subs)
    print(f"[+] Unsubscribed from: {topic}")

def list_subs():
    subs = load_subs()
    print(f"[*] Subscriptions ({len(subs)} total)")
    print()
    for s in subs:
        print(f"  {s['machine']:20} -> {s['topic']}")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "--topic":
        if len(args) < 2:
            print("Usage: subscribe.py --topic <topic>")
            return
        subscribe(args[1])
    elif args[0] == "--list":
        list_subs()
    elif args[0] == "--unsubscribe":
        if len(args) < 2:
            print("Usage: subscribe.py --unsubscribe <topic>")
            return
        unsubscribe(args[1])
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
