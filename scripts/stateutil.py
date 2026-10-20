#!/usr/bin/env python3
"""stateutil.py — utilitas state mesh: auto-resolve conflict git pada file JSON.

MASALAH (ditemukan 2026-10-20 di Kali):
  `sync.py --pull` memakai `git pull --rebase`. Kalau 2 mesin sama-sama
  mengubah file state yang sama (mis. broadcasts.json), rebase menghasilkan
  conflict marker ("<<<<<<< HEAD") di DALAM file JSON. Akibatnya:
    - file JSON jadi tidak valid -> broadcast.py / share.py crash
      (JSONDecodeError)
    - state hilang (isi kedua sisi tidak terbaca)
 ，偏偏 repo mesh sering berada di partisi NTFS (shared BlackArch<->Windows),
  yang memperbesar peluang file ter-truncate saat rebase.

SOLUSI:
  1. `_resolve_json_file()` — gabungkan dua sisi conflict jadi satu JSON valid
     (union by "id", tanpa duplikat), aman untuk list of dict.
  2. `resolve_all(state_dir)` — jalankan untuk semua *.json di state/.
  3. `rebase_continue()` — selesaikan rebase yang tersangkut.

Dipakai otomatis oleh sync.py setelah pull gagal.
"""
import json
import os
import subprocess
import sys

MARK_START = "<<<<<<<"
MARK_MID = "======="
MARK_END = ">>>>>>>"


def _parse_block(lines):
    """Parse satu sisi conflict jadi JSON (list/dict)."""
    txt = "\n".join(lines).strip()
    if not txt:
        return []
    try:
        return json.loads(txt)
    except Exception:
        pass
    # fallback: ambil objek JSON pertama yang lengkap
    for opener, closer in (("[", "]"), ("{", "}")):
        i, j = txt.find(opener), txt.rfind(closer)
        if i != -1 and j > i:
            try:
                return json.loads(txt[i : j + 1])
            except Exception:
                continue
    return []


def _split_conflict(raw):
    """Pecah file jadi (ours, theirs)."""
    ours, theirs, cur = [], [], None
    for ln in raw.split("\n"):
        if ln.startswith(MARK_START):
            cur = "ours"
            continue
        if ln.startswith(MARK_MID):
            cur = "theirs"
            continue
        if ln.startswith(MARK_END):
            cur = None
            continue
        if cur == "ours":
            ours.append(ln)
        elif cur == "theirs":
            theirs.append(ln)
    return ours, theirs


def _merge(a, b):
    """Union by 'id' (atau hash repr) tanpa duplikat."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            if k not in out:
                out[k] = v
            elif isinstance(out[k], list) and isinstance(v, list):
                out[k] = _merge(out[k], v)
        return out
    if isinstance(a, list) and isinstance(b, list):
        seen, out = set(), []
        for item in a + b:
            if isinstance(item, dict):
                k = item.get("id") or json.dumps(item, sort_keys=True)[:150]
            else:
                k = json.dumps(item, sort_keys=True)[:150] if not isinstance(item, str) else item
            if k in seen:
                continue
            seen.add(k)
            out.append(item)
        return out
    return b if b else a


def resolve_json_file(path):
    """Kalau file punya conflict marker, gabungkan jadi JSON valid.
    Return True kalau diperbaiki."""
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except Exception:
        return False
    if MARK_START not in raw:
        return False
    ours, theirs = _split_conflict(raw)
    a, b = _parse_block(ours), _parse_block(theirs)
    merged = _merge(a, b)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except Exception as e:
        print(f"[!] gagal menulis {path}: {e}")
        return False
    print(f"[+] conflict resolved: {os.path.basename(path)} ({len(merged) if hasattr(merged,'__len__') else '?'} item)")
    return True


def resolve_all(state_dir):
    fixed = []
    if not os.path.isdir(state_dir):
        return fixed
    for name in sorted(os.listdir(state_dir)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(state_dir, name)
        if os.path.isfile(p) and resolve_json_file(p):
            fixed.append(name)
    return fixed


def rebase_continue(repo=None, max_rounds=12):
    """Lanjutkan rebase yang tersangkut setelah conflict di-resolve.
    Loop: satu rebase bisa punya >1 conflict (per file). Setiap ronde:
    resolve -> git add -> rebase --continue, sampai selesai."""
    env = {**os.environ, "GIT_EDITOR": "true", "GIT_TERMINAL_PROMPT": "0"}
    for rnd in range(1, max_rounds + 1):
        try:
            r = subprocess.run(
                ["git", "rebase", "--continue"], capture_output=True, text=True, env=env
            )
        except Exception as e:
            return False, str(e)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            return True, out
        # conflict lagi -> resolve & coba lagi
        if "could not apply" in out or "CONFLICT" in out or "You must edit all merge conflicts" in out:
            fixed = resolve_all(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "state"))
            subprocess.run(["git", "add", "-A"], capture_output=True, text=True, env=env)
            if not fixed:
                # tidak ada file state yang bisa di-resolve -> conflict di file lain
                # (skip commit itu agar rebase tidak macet)
                subprocess.run(["git", "rebase", "--skip"], capture_output=True, text=True, env=env)
            continue
        if "No rebase in progress" in out or "nothing to do" in out:
            return True, out
        return False, out
    return False, "max rounds terlampaui"


if __name__ == "__main__":
    state_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "state"
    )
    state_dir = os.path.abspath(state_dir)
    fixed = resolve_all(state_dir)
    print(f"[*] {len(fixed)} file diperbaiki: {fixed if fixed else '-'}")
