#!/usr/bin/env python3
"""register.py — Daftar mesin ke mesh network.

Usage:
    python3 register.py --name "kali-attack" --role attack --ip 192.168.1.100
    python3 register.py --name "tablet" --role analysis --ip 192.168.1.101 --capabilities osint,analysis
"""
import argparse, json, os, socket, sys
from datetime import datetime

STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "state"))

def load_registry():
    path = os.path.join(STATE_DIR, "registry.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"machines": []}

def save_registry(registry):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "registry.json"), "w") as f:
        json.dump(registry, f, indent=2)

def register(name, role, ip, capabilities=None):
    registry = load_registry()
    # Remove old entry if exists
    registry["machines"] = [m for m in registry["machines"] if m["name"] != name]
    entry = {
        "name": name,
        "role": role,
        "ip": ip,
        "capabilities": capabilities or [],
        "hostname": socket.gethostname(),
        "last_seen": datetime.now().isoformat(),
        "status": "online",
    }
    registry["machines"].append(entry)
    save_registry(registry)
    print(f"[+] Registered: {name} ({role}) @ {ip}")
    print(f"    Capabilities: {', '.join(capabilities) if capabilities else 'none'}")
    print(f"    Hostname: {socket.gethostname()}")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--ip", required=True)
    p.add_argument("--capabilities", default=None, help="Comma-separated list")
    a = p.parse_args(args)
    capabilities = a.capabilities.split(",") if a.capabilities else []
    register(a.name, a.role, a.ip, capabilities)

if __name__ == "__main__":
    main()
