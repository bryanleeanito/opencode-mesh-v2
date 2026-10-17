#!/usr/bin/env python3
"""ideas.py — Tukar pikiran antar mesin.

Usage:
    python3 ideas.py --add "Pakai double-url encode bypass CF"
    python3 ideas.py --list
    python3 ideas.py --upvote <id>
"""
import argparse, json, os, platform, sys
from datetime import datetime

STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "state"))

def load_ideas():
    path = os.path.join(STATE_DIR, "ideas.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []

def save_ideas(ideas):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "ideas.json"), "w") as f:
        json.dump(ideas, f, indent=2)

def add_idea(text):
    ideas = load_ideas()
    idea_id = f"I-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    entry = {
        "id": idea_id,
        "text": text,
        "author": platform.node(),
        "created": datetime.now().isoformat(),
        "upvotes": 0,
    }
    ideas.append(entry)
    save_ideas(ideas)
    print(f"[+] Idea {idea_id}: {text}")

def list_ideas():
    ideas = load_ideas()
    print(f"[*] Ideas ({len(ideas)} total)")
    print()
    for i in ideas:
        print(f"  [{i['id']}] ({i['upvotes']} votes) {i['text']}")
        print(f"      by {i['author']} at {i['created'][:19]}")

def upvote(idea_id):
    ideas = load_ideas()
    for i in ideas:
        if i["id"] == idea_id:
            i["upvotes"] += 1
            save_ideas(ideas)
            print(f"[+] {idea_id} upvoted ({i['upvotes']} votes)")
            return
    print(f"[-] Idea {idea_id} not found")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "--add":
        if len(args) < 2:
            print("Usage: ideas.py --add <text>")
            return
        add_idea(" ".join(args[1:]))
    elif args[0] == "--list":
        list_ideas()
    elif args[0] == "--upvote":
        if len(args) < 2:
            print("Usage: ideas.py --upvote <id>")
            return
        upvote(args[1])
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
