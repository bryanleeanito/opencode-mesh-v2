#!/usr/bin/env python3
"""discover.py — Lihat semua mesin online di mesh.

Usage:
    python3 discover.py --all
    python3 discover.py --role attack
    python3 discover.py --capability osint
"""
import argparse, json, os, sys

STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "state"))

def load_registry():
    path = os.path.join(STATE_DIR, "registry.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"machines": []}

def discover_all():
    registry = load_registry()
    machines = registry.get("machines", [])
    print(f"[*] Online machines: {len(machines)}")
    print()
    for m in machines:
        print(f"  {m['name']:20} {m['role']:15} {m['ip']:16} {', '.join(m.get('capabilities', []))}")
    return machines

def discover_by_role(role):
    registry = load_registry()
    machines = [m for m in registry.get("machines", []) if m["role"] == role]
    print(f"[*] Machines with role '{role}': {len(machines)}")
    print()
    for m in machines:
        print(f"  {m['name']:20} {m['ip']:16} {', '.join(m.get('capabilities', []))}")
    return machines

def discover_by_capability(capability):
    registry = load_registry()
    machines = [m for m in registry.get("machines", []) if capability in m.get("capabilities", [])]
    print(f"[*] Machines with capability '{capability}': {len(machines)}")
    print()
    for m in machines:
        print(f"  {m['name']:20} {m['role']:15} {m['ip']:16}")
    return machines

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "--all":
        discover_all()
    elif args[0] == "--role":
        if len(args) < 2:
            print("Usage: discover.py --role <role>")
            return
        discover_by_role(args[1])
    elif args[0] == "--capability":
        if len(args) < 2:
            print("Usage: discover.py --capability <capability>")
            return
        discover_by_capability(args[1])
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
