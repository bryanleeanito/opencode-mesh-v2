#!/usr/bin/env python3
"""broadcast.py — Kirim pesan ke semua mesin di mesh.

Usage:
    python3 broadcast.py --message "Target pakai Cloudflare"
    python3 broadcast.py --type alert --message "SQLi ditemukan!"
    python3 broadcast.py --topic security --message "Patch dulu!"
"""
import argparse, json, os, sys
from datetime import datetime

STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "state"))

def load_broadcasts():
    path = os.path.join(STATE_DIR, "broadcasts.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []

def save_broadcasts(broadcasts):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "broadcasts.json"), "w") as f:
        json.dump(broadcasts, f, indent=2)

def broadcast(message, msg_type="info", topic=None):
    broadcasts = load_broadcasts()
    b_id = f"B-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    entry = {
        "id": b_id,
        "type": msg_type,
        "topic": topic,
        "message": message,
        "from": os.uname().nodename,
        "created": datetime.now().isoformat(),
    }
    broadcasts.append(entry)
    save_broadcasts(broadcasts)
    print(f"[+] Broadcast {b_id}: {message}")
    if topic:
        print(f"    Topic: {topic}")

def list_broadcasts(topic=None):
    broadcasts = load_broadcasts()
    if topic:
        broadcasts = [b for b in broadcasts if b.get("topic") == topic]
    print(f"[*] Broadcasts ({len(broadcasts)} total)")
    print()
    for b in broadcasts:
        topic_str = f"[{b.get('topic', 'general')}]" if b.get("topic") else ""
        print(f"  [{b['id']}] {topic_str} {b['message']}")
        print(f"      from {b['from']} at {b['created'][:19]}")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "--message":
        if len(args) < 2:
            print("Usage: broadcast.py --message <message>")
            return
        msg = " ".join(args[1:])
        broadcast(msg)
    elif args[0] == "--type":
        if len(args) < 4:
            print("Usage: broadcast.py --type <type> --message <message>")
            return
        msg_type = args[1]
        msg_idx = args.index("--message")
        msg = " ".join(args[msg_idx + 1:])
        broadcast(msg, msg_type)
    elif args[0] == "--topic":
        if len(args) < 4:
            print("Usage: broadcast.py --topic <topic> --message <message>")
            return
        topic = args[1]
        msg_idx = args.index("--message")
        msg = " ".join(args[msg_idx + 1:])
        broadcast(msg, topic=topic)
    elif args[0] == "--list":
        topic = None
        if "--topic" in args:
            topic = args[args.index("--topic") + 1]
        list_broadcasts(topic)
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
