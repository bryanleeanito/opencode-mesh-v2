#!/usr/bin/env python3
"""sync.py — Sinkronisasi state antar mesin via git.

Usage:
    python3 sync.py --pull
    python3 sync.py --push
    python3 sync.py --status
"""
import argparse, json, os, subprocess, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stateutil  # auto-resolve conflict git pada state/*.json

STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "state"))

def git_pull():
    print("[*] Pulling updates...")
    try:
        # State lokal yang belum di-commit (mis. hasil register/broadcast)
        # BUKAN konflik — itu bus yang belum terkirim. Commit dulu supaya
        # `git pull --rebase` tidak menolak dengan "unstaged changes".
        r0 = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if r0.stdout.strip():
            subprocess.run(["git", "add", "-A"], check=True)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            subprocess.run(["git", "commit", "-m", f"mesh-sync (pre-pull): {ts}"], check=True)
            print("[*] state lokal di-commit dulu (pre-pull)")
        r = subprocess.run(["git", "pull", "--rebase"], capture_output=True, text=True)
        if r.returncode == 0:
            print("[+] Pull successful")
            return True
        # --- Conflict handling (2026-10-20) ---
        # git pull --rebase bisa menyisipkan conflict marker ke file state/*.json
        # -> JSON rusak -> semua script mesh crash. Resolusi otomatis + lanjut rebase.
        print("[!] Pull gagal — cek & auto-resolve conflict state...")
        fixed = stateutil.resolve_all(STATE_DIR)
        if fixed:
            subprocess.run(["git", "add", "-A"], capture_output=True, text=True)
            ok, out = stateutil.rebase_continue()
            if ok:
                print("[+] Conflict ter-resolve, rebase selesai")
                r2 = subprocess.run(["git", "pull", "--rebase"], capture_output=True, text=True)
                if r2.returncode == 0:
                    print("[+] Pull successful (setelah resolve)")
                    return True
            else:
                print(f"[-] rebase --continue gagal: {out.strip()[:300]}")
        else:
            print(f"[-] Pull failed: {r.stderr.strip()[:400]}")
        # Fallback: pastikan file state minimal valid JSON agar mesh tidak crash
        stateutil.resolve_all(STATE_DIR)
        return False
    except Exception as e:
        print(f"[-] Error: {e}")
        return False

def git_push():
    print("[*] Pushing updates...")
    try:
        # Alur: tree dirty -> commit dulu. Tree bersih tapi ada commit
        # lokal belum ter-push -> langsung push. Bersih + sinkron -> selesai.
        r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if r.stdout.strip():
            subprocess.run(["git", "add", "-A"], check=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            subprocess.run(["git", "commit", "-m", f"mesh-sync: {timestamp}"], check=True)
        else:
            ra = subprocess.run(["git", "rev-list", "@{upstream}..HEAD", "--count"],
                                capture_output=True, text=True)
            if ra.stdout.strip() == "0":
                print("[*] Git clean — tidak ada yang perlu di-push")
                return True
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
