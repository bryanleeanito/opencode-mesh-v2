#!/usr/bin/env python3
"""mesh_status.py — Presence + sinkron otomatis mesh (satu perintah).

Usage:
    python3 mesh_status.py                 # pull -> presence(online) -> push -> tabel
    python3 mesh_status.py --status idle   # tandai idle (default online)
    python3 mesh_status.py --local         # tanpa git (presence + tabel saja)
    python3 mesh_status.py --name <nama>   # set mesin ini (sekali) lalu simpan
    python3 mesh_status.py --install       # pasang auto-sync + boot-sync + self-test
    python3 mesh_status.py --uninstall     # lepas pemasangan --install
    python3 mesh_status.py --cron          # mode internal scheduler (hening, rate-limit)

Catatan:
    - status "online" = scheduler/mesin hidup, BUKAN user aktif.
    - presence per mesin: state/presence/<nama>.json (last_seen = epoch UTC).
    - identitas mesin: ~/.mesh_self.json (DI LUAR repo — kalau disimpan di
      state/, sync.py `git add -A` akan push-nya dan nama mesin lain ketimpa).
    - env utk tes: MESH_STATE_DIR (override state dir),
      MESH_SELF_FILE (override file identitas).
"""
import json, os, shutil, socket, subprocess, sys, time
from datetime import datetime, timezone

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
STATE_DIR = os.environ.get("MESH_STATE_DIR") or os.path.join(REPO_DIR, "state")
SELF_FILE = os.environ.get("MESH_SELF_FILE") or os.path.join(
    os.path.expanduser("~"), ".mesh_self.json")
PRESENCE_DIR = os.path.join(STATE_DIR, "presence")
ERROR_LOG = os.path.join(STATE_DIR, "last_error.log")
CRON_MARKER = "# mesh-presence"
BATAS_KRONS = 600  # detik: rate-limit push presence (hindari ~96 commit/hari)
NAMA_TASK_WIN = ["MeshPresence", "MeshPresenceBoot"]


# ---------- json dasar ----------

def load_json(path, default=None):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except ValueError:
            return default
    return default


def save_json(path, data):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_registry():
    data = load_json(os.path.join(STATE_DIR, "registry.json"), {"machines": []})
    if not isinstance(data, dict) or "machines" not in data:
        return {"machines": []}
    return data


# ---------- presence ----------

def lokal_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # cuma set route, tanpa kirim paket
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def baca_presence(nama):
    return load_json(os.path.join(PRESENCE_DIR, nama + ".json"))


def tulis_presence(nama, status):
    data = {
        "name": nama,
        "status": status,
        "last_seen": int(time.time()),  # epoch UTC — kebal DST/timezone beda
        "updated_iso": datetime.now(timezone.utc).isoformat(),
        "ip": lokal_ip(),
        "hostname": socket.gethostname(),
    }
    save_json(os.path.join(PRESENCE_DIR, nama + ".json"), data)
    return data


def umur_str(epoch, now=None):
    if now is None:
        now = time.time()
    d = int(now) - int(epoch)
    if d < 0:
        d = 0
    if d < 60:
        return "baru saja"
    if d < 3600:
        return "%d mnt lalu" % (d // 60)
    return "%d jam lalu" % (d // 3600)


def boleh_push_cron(last_seen, now, batas=BATAS_KRONS):
    if last_seen is None:
        return True
    return (now - last_seen) >= batas


# ---------- git (lewat sync.py + guard anti-hang) ----------

def git_env():
    env = dict(os.environ)
    # cron tidak punya TTY: gagal cepat, jangan nunggu prompt kredensial selamanya
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def catat_error(pesan):
    folder = os.path.dirname(ERROR_LOG)
    if not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write("%s %s\n" % (datetime.now(timezone.utc).isoformat(), pesan))


def jalankan_sync(cmd, hening):
    """Jalankan sync.py --pull / --push (cwd selalu REPO_DIR)."""
    try:
        p = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "sync.py"), cmd],
            capture_output=True, text=True, env=git_env(),
            cwd=REPO_DIR, timeout=120)
    except subprocess.TimeoutExpired:
        catat_error("%s timeout 120s" % cmd)
        if not hening:
            print("[-] %s: timeout" % cmd)
        return False
    if p.returncode != 0:
        alasan = (p.stderr or p.stdout or "").strip()[:300]
        catat_error("%s gagal (rc=%d): %s" % (cmd, p.returncode, alasan))
        if not hening:
            print("[-] %s gagal (detail: state/last_error.log)" % cmd)
        return False
    return True


def jalankan_git(args, timeout=30):
    git = shutil.which("git") or "git"
    try:
        return subprocess.run([git] + args, cwd=REPO_DIR,
                              capture_output=True, text=True,
                              env=git_env(), timeout=timeout)
    except Exception:
        return None


def push_retry(hening):
    """Push; kalau gagal, tiap retry didahului pull. Maks 3x."""
    for i in range(3):
        if not hening:
            print("[*] Push (percobaan %d/3)..." % (i + 1))
        if jalankan_sync("--push", hening):
            return True
        if i < 2:
            jalankan_sync("--pull", hening)
    jalankan_git(["rebase", "--abort"])  # bersihkan sisa rebase yang mogok
    catat_error("push gagal setelah 3 percobaan")
    if not hening:
        print("[-] push gagal setelah 3 percobaan (detail: state/last_error.log)")
    return False


# ---------- tabel presence ----------

def tabel_presence():
    mesin = load_registry().get("machines", [])
    if not mesin:
        print("[*] registry kosong — jalankan register.py dulu")
        return
    print("[*] Presence mesh:")
    print("    %-16s %-12s %-15s %-8s %s" %
          ("nama", "role", "ip", "status", "terakhir"))
    now = time.time()
    for m in mesin:
        nama = m.get("name", "?")
        pres = baca_presence(nama)
        last = None
        if isinstance(pres, dict) and pres.get("last_seen") is not None:
            try:
                last = int(pres["last_seen"])
            except (TypeError, ValueError):
                last = None
        if last is None:
            tanda, status, umur = "!", "-", "-"
        else:
            status = pres.get("status", "-")
            umur = umur_str(last, now)
            tanda = "!" if (now - last) > 3600 else " "
        print("  %s %-16s %-12s %-15s %-8s %s" %
              (tanda, nama, m.get("role", "-"), m.get("ip", "-"), status, umur))


# ---------- install / uninstall ----------

def baris_cron():
    py = sys.executable
    return [
        "*/15 * * * * cd '%s' && '%s' scripts/mesh_status.py --cron %s" %
        (REPO_DIR, py, CRON_MARKER),
        "@reboot cd '%s' && '%s' scripts/mesh_status.py --cron %s" %
        (REPO_DIR, py, CRON_MARKER),
    ]


def install_posix():
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True,
                           timeout=30)
    except Exception as e:
        print("[-] gagal baca crontab: %s" % e)
        return False
    lama = r.stdout if r.returncode == 0 else ""  # rc=1 = belum ada crontab
    # buang baris marker lama, tulis ulang keduanya (idempoten)
    sisa = [l for l in lama.splitlines() if CRON_MARKER not in l]
    data = "\n".join(sisa + baris_cron()) + "\n"
    try:
        p = subprocess.run(["crontab", "-"], input=data,
                           capture_output=True, text=True, timeout=30)
    except Exception as e:
        print("[-] gagal menulis crontab: %s" % e)
        return False
    if p.returncode != 0:
        print("[-] gagal menulis crontab: %s" % (p.stderr or p.stdout).strip())
        return False
    for l in baris_cron():
        print("[+] cron: %s" % l)
    return True


def tr_windows():
    return '"%s" "%s" --cron' % (
        sys.executable, os.path.join(SCRIPTS_DIR, "mesh_status.py"))


def install_windows():
    ok = True
    jadwal = [(NAMA_TASK_WIN[0], ["/SC", "MINUTE", "/MO", "15"]),
              (NAMA_TASK_WIN[1], ["/SC", "ONLOGON"])]
    for nama, skedul in jadwal:
        try:
            p = subprocess.run(
                ["schtasks", "/Create", "/F", "/TN", nama] + skedul +
                ["/TR", tr_windows()],
                capture_output=True, text=True, timeout=30)
        except Exception as e:
            print("[-] gagal bikin %s: %s" % (nama, e))
            ok = False
            continue
        if p.returncode == 0:
            print("[+] task: %s (%s)" % (nama, " ".join(skedul)))
        else:
            print("[-] gagal bikin %s: %s" %
                  (nama, ((p.stdout or "") + (p.stderr or "")).strip()))
            ok = False
    return ok


def self_test():
    """Jalankan --cron sekali — bukti E2E (pull+presence+push) benar-benar jalan."""
    try:
        p = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "mesh_status.py"),
             "--cron"],
            capture_output=True, text=True, env=git_env(),
            cwd=REPO_DIR, timeout=180)
    except subprocess.TimeoutExpired:
        print("[-] self-test: FAIL (timeout)")
        return False
    if p.returncode == 0:
        print("[+] self-test: PASS")
        return True
    print("[-] self-test: FAIL (rc=%d) — jalankan manual "
          "'mesh_status.py --cron' untuk lihat error" % p.returncode)
    keluar = ((p.stdout or "") + (p.stderr or "")).strip()
    if keluar:
        print("    " + keluar[:500].replace("\n", "\n    "))
    catat_error("self-test gagal (rc=%d)" % p.returncode)
    return False


def install():
    if os.name == "nt":
        ok = install_windows()
    else:
        ok = install_posix()
    if not ok:
        return False
    print("[*] self-test (sekali jalan)...")
    return self_test()


def uninstall():
    if os.name == "nt":
        for nama in NAMA_TASK_WIN:
            try:
                p = subprocess.run(["schtasks", "/Delete", "/F", "/TN", nama],
                                   capture_output=True, text=True, timeout=30)
            except Exception as e:
                print("[-] %s: %s" % (nama, e))
                continue
            if p.returncode == 0:
                print("[+] task dihapus: %s" % nama)
            else:
                print("[*] %s tidak ditemukan / tidak bisa dihapus" % nama)
        return True
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True,
                           timeout=30)
    except Exception as e:
        print("[-] gagal baca crontab: %s" % e)
        return False
    if r.returncode != 0:
        print("[*] crontab kosong — tidak ada yang dilepas")
        return True
    sisa = [l for l in r.stdout.splitlines() if CRON_MARKER not in l]
    data = "\n".join(sisa) + ("\n" if sisa else "")
    try:
        p = subprocess.run(["crontab", "-"], input=data,
                           capture_output=True, text=True, timeout=30)
    except Exception as e:
        print("[-] gagal menulis crontab: %s" % e)
        return False
    if p.returncode != 0:
        print("[-] gagal menulis crontab: %s" % (p.stderr or p.stdout).strip())
        return False
    print("[+] baris %s dihapus dari crontab" % CRON_MARKER)
    return True


# ---------- argumen & main ----------

def parse_args(argv):
    o = {"local": False, "cron": False, "install": False, "uninstall": False,
         "help": False, "name": None, "status": "online"}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--local":
            o["local"] = True
        elif a == "--cron":
            o["cron"] = True
        elif a == "--install":
            o["install"] = True
        elif a == "--uninstall":
            o["uninstall"] = True
        elif a in ("--help", "-h"):
            o["help"] = True
        elif a == "--name":
            if i + 1 >= len(argv):
                print("[-] --name butuh nilai")
                return None
            i += 1
            o["name"] = argv[i]
        elif a == "--status":
            if i + 1 >= len(argv):
                print("[-] --status butuh nilai (online/idle)")
                return None
            i += 1
            o["status"] = argv[i]
        else:
            print("[-] argumen tak dikenal: %s" % a)
            return None
        i += 1
    return o


def main():
    argv = sys.argv[1:]
    # Tanpa argumen = alur penuh (pull -> presence -> push -> tabel), sesuai docstring.
    o = parse_args(argv)
    if o is None:
        print(__doc__)
        return 1
    if o["help"]:
        print(__doc__)
        return 0
    if o["uninstall"]:
        return 0 if uninstall() else 1
    if o["install"]:
        return 0 if install() else 1

    hening = o["cron"]
    lokal = o["local"]
    if not hening and o["status"] not in ("online", "idle"):
        print("[-] status harus online/idle (dapat: %s)" % o["status"])
        return 1

    # --- identitas mesin ---
    daftar = [m.get("name") for m in load_registry().get("machines", [])]
    if o["name"] is not None:
        if o["name"] not in daftar:
            print("[-] '%s' belum terdaftar — jalankan register.py dulu"
                  % o["name"])
            return 1
        save_json(SELF_FILE, {"name": o["name"]})
        nama = o["name"]
    else:
        d = load_json(SELF_FILE)
        if not isinstance(d, dict) or "name" not in d:
            pesan = ("belum set nama: jalankan sekali 'mesh_status.py "
                     "--name <nama>' (nama harus terdaftar di registry)")
            if hening:
                catat_error(pesan)
            else:
                print("[-] " + pesan)
            return 1
        nama = d["name"]
        if nama not in daftar:
            print("[-] '%s' belum terdaftar — jalankan register.py dulu"
                  % nama)
            return 1

    # --- 1. pull (selalu, kecuali --local) ---
    pull_ok = True
    if not lokal:
        if not hening:
            print("[*] Pull...")
        pull_ok = jalankan_sync("--pull", hening)

    # --- 2. presence (rate-limited di mode cron) ---
    pres = baca_presence(nama)
    last = pres.get("last_seen") if isinstance(pres, dict) else None
    if hening and not boleh_push_cron(last, time.time()):
        # sudah fresh — pull saja cukup, tidak usah commit
        return 0 if pull_ok else 1
    status = "online" if hening else o["status"]
    tulis_presence(nama, status)
    if not hening:
        print("[+] presence: %s (%s)" % (nama, status))

    # --- 3. push dengan retry ---
    push_ok = True
    if not lokal:
        push_ok = push_retry(hening)

    # --- 4. tabel (mode normal saja; cron hening) ---
    if not hening:
        tabel_presence()

    return 0 if (pull_ok and push_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
