#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mesh_integrator.py — Integrasi OpenCode Mesh dengan Ptoolsdexeroid + windev-specialist.

Bisa langsung eksekusi kit dari repo lain via mesh.
Semua perintah read-only / non-destruktif kecuali diarahkan ke target terotorisasi.

Usage:
    python3 mesh_integrator.py list-kits
    python3 mesh_integrator.py run-kit --kit waf-bypass --command "encode --payload test --method double-url"
    python3 mesh_integrator.py run-kit --kit sherlock-osint --command "username --target testuser --limit 5"
    python3 mesh_integrator.py delegate-kit --to kali-attack --kit waf-bypass --command "..."
    python3 mesh_integrator.py mesh-status
"""
import argparse, json, os, platform, subprocess, sys
from datetime import datetime

MESH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.abspath(os.path.join(MESH_DIR, "state"))

# Path ke repo lain (bisa di-override via env var)
PTREPO = os.environ.get("PTOOLSDEXEROID_PATH", os.path.join(os.path.dirname(MESH_DIR), "Ptoolsdexeroid"))
WINREPO = os.environ.get("WINDEV_SPECIALIST_PATH", os.path.join(os.path.dirname(MESH_DIR), "windev-specialist"))

# Kit registry: nama kit -> path ke script
# Ptoolsdexeroid: pentest/CTF/bypass
KIT_PT = {
    "waf-bypass": f"{PTREPO}/kits/waf-bypass/waf_bypass.py",
    "cloudflare-bypass": f"{PTREPO}/kits/cloudflare-bypass/cf_bypass.py",
    "sqli-helper": f"{PTREPO}/kits/sqli-helper/sqli_helper.py",
    "payload-generator": f"{PTREPO}/kits/payload-generator/payload_gen.py",
    "webshell-manager": f"{PTREPO}/kits/webshell-manager/webshell_manager.py",
    "firewall-bypass": f"{PTREPO}/kits/firewall-bypass/fw_bypass.py",
    "ip-changer": f"{PTREPO}/kits/ip-changer/ip_changer.py",
    "ip-anti-lock": f"{PTREPO}/kits/ip-anti-lock/anti_lock.py",
    "defense-counter": f"{PTREPO}/kits/defense-counter/defense_counter.py",
    "jwt-toolkit": f"{PTREPO}/kits/jwt-toolkit/jwt_toolkit.py",
    "rev-toolkit": f"{PTREPO}/kits/rev-toolkit/rev_toolkit.py",
    "crypto-specialist": f"{PTREPO}/kits/crypto-specialist/crypto_specialist.py",
    "rev-specialist": f"{PTREPO}/kits/rev-specialist/rev_specialist.py",
    "ctf-decoder": f"{PTREPO}/kits/ctf-decoder/decode.py",
    "ctf-crypto": f"{PTREPO}/kits/ctf-crypto/classics.py",
    "ctf-forensics": f"{PTREPO}/kits/ctf-forensics/probe.py",
    "ctf-web": f"{PTREPO}/kits/ctf-web/recon_ctf.py",
    "ctf-misc-solver": f"{PTREPO}/kits/ctf-misc-solver/misc_solver.py",
    "ctf-drills": f"{PTREPO}/kits/ctf-drills/gen_drills.py",
    "sherlock-osint": f"{PTREPO}/kits/sherlock-osint/sherlock.py",
    "security-protect": f"{PTREPO}/kits/security-protect/security_protect.py",
    "extreme-efficiency": f"{PTREPO}/kits/extreme-efficiency/extreme_mode.py",
    "elementor-bypass": f"{PTREPO}/kits/elementor-bypass/elementor_bypass.py",
}

# windev-specialist: dev + sysadmin untuk mesin Windows
# Prefix "windev-" distinguishes it from Ptoolsdexeroid kits.
KIT_WIN = {
    "windev-env-report": f"{WINREPO}/tools/sysadmin/env_report/env_report.py",
    "windev-jsonc-check": f"{WINREPO}/tools/dev/jsonc_check/jsonc_check.py",
    "windev-ps51-lint": f"{WINREPO}/tools/dev/ps51_lint/ps51_lint.py",
}

# Gabungan (dipakai run-kit / delegate-kit)
KIT_REGISTRY = {**KIT_PT, **KIT_WIN}

# Kategori untuk list-kits (bukan lagi deteksi via substring nama kit)
KATEGORI = [
    ("Ptoolsdexeroid (Pentest/CTF/Bypass)", sorted(KIT_PT)),
    ("windev-specialist (Windows Dev/Sysadmin)", sorted(KIT_WIN)),
]

def load_registry():
    path = os.path.join(STATE_DIR, "registry.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"machines": []}

def list_kits():
    print("[*] Available kits via mesh integrator")
    print()
    for cat, kits in KATEGORI:
        print(f"--- {cat} ---")
        for k in kits:
            path = KIT_REGISTRY[k]
            exists = os.path.exists(path)
            status = "✓" if exists else "✗"
            print(f"  {status} {k}")
    print()
    print(f"Total: {len(KIT_REGISTRY)} kits ({len(KIT_PT)} Ptoolsdexeroid + {len(KIT_WIN)} windev)")

def run_kit(kit, command):
    path = KIT_REGISTRY.get(kit)
    if not path:
        print(f"[-] Kit tidak dikenal: {kit}")
        print(f"    Available: {', '.join(sorted(KIT_REGISTRY.keys()))}")
        return False
    if not os.path.exists(path):
        print(f"[-] Kit script tidak ada: {path}")
        print(f"    Clone repo sumbernya: Ptoolsdexeroid -> {PTREPO} | "
              f"windev-specialist -> {WINREPO}")
        return False
    print(f"[*] Running kit: {kit}")
    print(f"    Command: {command}")
    print()
    try:
        r = subprocess.run(["python3", path] + command.split(), capture_output=True, text=True, timeout=300)
        print(r.stdout)
        if r.stderr:
            print("STDERR:", r.stderr)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print("[-] Timeout (5 menit)")
        return False
    except Exception as e:
        print(f"[-] Error: {e}")
        return False

def delegate_kit(to_machine, kit, command):
    # Simpan delegation ke state untuk mesin tujuan pickup
    handoffs_path = os.path.join(STATE_DIR, "handoffs.json")
    if os.path.exists(handoffs_path):
        with open(handoffs_path) as f:
            handoffs = json.load(f)
    else:
        handoffs = []
    h_id = f"K-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    entry = {
        "id": h_id,
        "to": to_machine,
        "kit": kit,
        "command": command,
        "status": "pending",
        "from": platform.node(),
        "created": datetime.now().isoformat(),
    }
    handoffs.append(entry)
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(handoffs_path, "w") as f:
        json.dump(handoffs, f, indent=2)
    print(f"[+] Kit delegation {h_id} -> {to_machine}")
    print(f"    Kit: {kit}")
    print(f"    Command: {command}")
    print(f"    Status: pending")

def mesh_status():
    registry = load_registry()
    machines = registry.get("machines", [])
    print("[*] Mesh status")
    print()
    print(f"Machines registered: {len(machines)}")
    for m in machines:
        caps = ", ".join(m.get("capabilities", []))
        print(f"  {m['name']:20} {m['role']:15} {m['ip']:16} [{caps}]")
    print()
    print(f"Kits registered: {len(KIT_REGISTRY)} "
          f"({len(KIT_PT)} Ptoolsdexeroid + {len(KIT_WIN)} windev)")
    pt_exists = os.path.exists(PTREPO)
    win_exists = os.path.exists(WINREPO)
    print(f"Ptoolsdexeroid: {'✓' if pt_exists else '✗'} ({PTREPO})")
    print(f"windev-specialist: {'✓' if win_exists else '✗'} ({WINREPO})")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "list-kits":
        list_kits()
    elif cmd == "run-kit":
        p = argparse.ArgumentParser()
        p.add_argument("--kit", required=True)
        p.add_argument("--command", required=True)
        a = p.parse_args(args[1:])
        run_kit(a.kit, a.command)
    elif cmd == "delegate-kit":
        p = argparse.ArgumentParser()
        p.add_argument("--to", required=True)
        p.add_argument("--kit", required=True)
        p.add_argument("--command", required=True)
        a = p.parse_args(args[1:])
        delegate_kit(a.to, a.kit, a.command)
    elif cmd == "mesh-status":
        mesh_status()
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
