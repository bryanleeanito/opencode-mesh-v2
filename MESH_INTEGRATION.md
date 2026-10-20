<<<<<<< HEAD
# MESH_INTEGRATION.md — Integrasi 3 Repo OpenCode Mesh

Dibuat 2026-10-16. Diperbarui 2026-10-17 (setup khusus Tab Termux+proot Ubuntu).

## Repo yang Diintegrasi

| Repo | Fungsi | Path (default) |
|---|---|---|
| `Ptoolsdexeroid` | 35 kit pentest/CTF/bypass | `../Ptoolsdexeroid/` |
| `windev-specialist` | Windows dev toolkit | `../windev-specialist/` |
| `opencode-mesh-v2` | Koordinasi mesh (ini) | `.` |

## Aktivasi 1 Perintah (disarankan)

Daripada 7 langkah manual, ada bootstrap script yang idempoten (aman
diulang, yang sudah beres tidak diulang).

**Linux / macOS / Termux-proot:**

```bash
git clone https://github.com/bryanleeanito/opencode-mesh-v2.git
cd opencode-mesh-v2
bash scripts/mesh_bootstrap.sh --name <nama-mesin> --role <role> \
  --ip <ip> --capabilities <a,b,c> --with-kits
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/bryanleeanito/opencode-mesh-v2.git
cd opencode-mesh-v2
powershell -ExecutionPolicy Bypass -File scripts\mesh_bootstrap.ps1 `
  -Name <nama-mesin> -Role <role> -Ip <ip> -Capabilities <a,b,c> -WithKits
```

Yang dilakukan bootstrap:

| # | Langkah | Catatan |
|---|---|---|
| 1 | Cek/clone repo mesh | skip kalau sudah lengkap |
| 2 | Clone repo kit (`--with-kits`) | Ptoolsdexeroid + windev-specialist |
| 3 | Cek kredensial git | `credential.helper=store` → push 2 arah |
| 4 | Register mesin | skip dengan `--skip-register` |
| 5 | Set identitas + presence | `~/.mesh_self.json` |
| 6 | Pasang auto-sync | cron `*/15` + `@reboot` / schtasks + self-test |
| 7 | Nyalakan cron daemon | Linux/proot: `pgrep -x cron` + autostart `~/.bashrc` |
| 8 | Verifikasi | crontab, daemon, presence, `git push --dry-run` |

Role yang dipakai: `attack`, `analysis`, `development`, `pentest`, `ctf`.

## Setup di Setiap Mesin (manual)

```bash
# 1. Clone semua repo
git clone https://github.com/bryanleeanito/Ptoolsdexeroid.git
git clone https://github.com/bryanleeanito/windev-specialist.git
git clone https://github.com/bryanleeanito/opencode-mesh-v2.git

# 2. Masuk ke mesh
cd opencode-mesh-v2

# 3. Register mesin
python3 scripts/register.py --name "kali-attack" --role attack --ip 192.168.1.100

# 4. Sinkron
python3 scripts/sync.py --pull
```

## Auto-sync & Presence (mesh_status.py)

Satu perintah sync + status siapa yang hidup. `--install` sekali di tiap
mesin — setelah itu semua jalan otomatis (tiap 15 menit + saat boot),
tanpa nyusun cron/manual:

```bash
# 5. Set nama mesin ini (sekali) lalu pasang auto-sync
python3 scripts/mesh_status.py --name <nama-terdaftar>
python3 scripts/mesh_status.py --install   # cron/schtasks + self-test

# Cek presence kapan saja (pull -> update -> push -> tabel)
python3 scripts/mesh_status.py

# Mode offline / tanpa git (tabel saja)
python3 scripts/mesh_status.py --local

# Lepas auto-sync
python3 scripts/mesh_status.py --uninstall
```

- presence per mesin: `state/presence/<nama>.json` (last_seen epoch UTC).
- `online` = scheduler/mesin hidup, bukan user aktif; `!` = stale > 1 jam.
- identitas mesin: `~/.mesh_self.json` (di luar repo, tidak ikut push).
- di mode cron, push presence di-rate-limit 10 menit (hemat commit);
  gagal sync dicatat ke `state/last_error.log`.

## Setup khusus: Tab via Termux + proot Ubuntu

Tab jalanin OpenCode di **proot Ubuntu (glibc, ARM64)** — platform resmi yang
didukung OpenCode (ada binary standalone `linux-arm64`). Di DALAM proot:

```bash
# 1. Dependensi
apt update && apt install -y git curl python3 unzip

# 2. OpenCode V2 (native ARM64 glibc)
curl -fsSL https://opencode.ai/v2/install | bash
#   alternatif: apt install nodejs npm && npm install -g @opencode/cli
opencode --version   # bukti terpasang

# 3. Git identity + credentials (WAJIB — mesh itu git push)
git config --global user.name "kzldx"
git config --global user.email "kzldx@users.noreply.github.com"
git config --global credential.helper store   # sekali ketik PAT, tersimpan
#   alternatif: bikin SSH key -> tambah ke akun GitHub

# 4. Masuk mesh
git clone https://github.com/bryanleeanito/opencode-mesh-v2.git ~/opencode-mesh-v2
cd ~/opencode-mesh-v2
python3 scripts/register.py --name tablet-analysis --role analysis \
  --ip "$(hostname -I | awk '{print $1}')" --capabilities osint,analysis,reporting
python3 scripts/sync.py --pull
python3 scripts/discover.py --all
```

Jebakan proot/Termux:

- **Cron daemon tidak auto hidup.** Proot tanpa systemd → `crontab` yang
  terpasang tidak dieksekusi apa pun. Jalankan `/usr/sbin/cron` manual.
  Fix permanen (taruh di `~/.bashrc` agar hidup tiap `proot-distro login`):
  ```bash
  if [ -x /usr/sbin/cron ] && ! pgrep -x cron >/dev/null 2>&1; then
    /usr/sbin/cron 2>/dev/null
  fi
  ```
  Verifikasi: `ps -ef | grep [s]bin/cron` (ada proses = cron hidup).
- **`%` di crontab berarti baris baru.** `date '+%H:%M:%S'` jadi dua
  perintah dan job gagal tanpa error terlihat. Escape pakai `\%` atau
  `date +\%H:\%M:\%S`.
- **Tidak ada syslog/MTA di proot** → output job cron di-"discard", jadi
  error cron tidak muncul. Pantau `state/last_error.log` (ditulis
  `mesh_status.py`) dan `state/presence/<nama>.json`.
- **`pkill -f 'cron -f'` bisa membunuh shell sendiri** (pattern match ke
  command line). Pakai `pkill -x cron`.
- **Repo di `~/`, jangan `/sdcard`** — filesystem eksternal Android = noexec
  + permission aneh, binary/script gagal jalan.
- **Push mesh butuh auth GitHub**: transport = `git push` HTTPS. Tanpa PAT
  (`credential.helper store`) atau SSH key, kamu bisa PULL tapi tidak bisa
  KIRIM pesan — mesh jadi satu arah. Cek cepat: `git push --dry-run origin HEAD`.
- Proot tanpa systemd — OpenCode service start on-demand; kalau macet:
  `opencode service status` / `opencode service restart`, atau fallback
  `opencode --standalone`.
- Supaya sesi tidak mati saat layar off: `termux-wake-lock`.
- IP proot = IP Android (jaringan dibagikan) — `hostname -I` langsung dapat
  IP LAN yang terlihat mesin lain.
- Alur harian: `sync.py --pull` awal sesi → kerja/kirim pesan →
  `sync.py --push` sebelum tutup (commit dulu kalau ada perubahan lokal,
  lalu pull baru push).

## Integrasi ke OpenCode (plugin `mesh-sync`)

Plugin di `~/.config/opencode/plugins/mesh-sync/index.ts` (pola default
export `{ id, setup }`, sama seperti plugin audit-log/disk-guard):

- hook `context` → menyuntik ringkasan mesh ke system prompt: daftar
  mesin + status online/offline + pesan broadcast terakhir (max 1×/10 menit
  supaya hemat token);
- hook `prompt` → presence ping ke mesh (spawn detached `mesh_status.py
  --cron`, max 1×/10 menit, tidak pernah memblokir request);
- monitoring: push gagal (`state/last_error.log`) dan presence basi
  > 20 menit (indikasi cron daemon mati) dilaporkan sebagai baris
  PERINGATAN di system prompt — penting karena proot tidak punya syslog,
  kegagalan sync kalau tidak dicek ini senyap;
- jejak di `~/.local/share/opencode/mesh-sync.log`.

Regenerasi/matikan: hapus folder plugin itu (atau `mv` ke luar
`plugins/`), lalu restart OpenCode.

## Cara Eksekusi Kit Lewat Mesh

### 1. Lihat semua kit
```bash
python3 scripts/mesh_integrator.py list-kits
```
Total 26 kit: 23 Ptoolsdexeroid (pentest/CTF/bypass) + 3 windev-specialist
(`windev-env-report`, `windev-jsonc-check`, `windev-ps51-lint`).

### 2. Jalankan kit langsung
```bash
# Contoh: WAF bypass encode
python3 scripts/mesh_integrator.py run-kit --kit waf-bypass --command "encode --payload 'test' --method double-url"

# Contoh: Sherlock OSINT
python3 scripts/mesh_integrator.py run-kit --kit sherlock-osint --command "username --target testuser --limit 5"
```

### 3. Delegasi ke mesin lain
```bash
# Delegasi task + kit ke mesin lain
python3 scripts/mesh_integrator.py delegate-kit --to kali-attack --kit waf-bypass --command "encode --payload 'test' --method double-url"
```

## Alur Kerja Tiga Mesin

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   KALI      │    │  TABLET     │    │   WINDOWS   │
│  (Attack)   │    │  (Analysis) │    │ (Dev+DevOps)│
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │ 1. Attack        │                  │
       │    run kit       │                  │
       ▼                  │                  │
mesh_v2 <──────────────────┼──────────────────┤
       │                  │                  │
       │                  │ 2. Analysis      │
       │                  │    run kit       │
       │                  ▼                  │
       │                  │                  │
       │                  │ 3. Dev           │
       │                  │    build/deploy  │
       │                  │                  │
       └──────────────────┴──────────────────┘
       4. Share findings via mesh (share.py / broadcast.py)
```

## Contoh Kerja Sama

### Skenario: Pentest Target

1. **Kali (Attack)**:
   ```bash
   python3 scripts/mesh_integrator.py run-kit --kit waf-bypass --command "method --target target.com"
   python3 scripts/share.py --type finding --message "WAF Cloudflare detected"
   ```

2. **Tablet (Analysis)**:
   ```bash
   python3 scripts/discover.py --all
   python3 scripts/share.py --list
   python3 scripts/mesh_integrator.py run-kit --kit sherlock-osint --command "domain --target target.com"
   ```

3. **Windows (Dev/DevOps)**:
   ```bash
   python3 scripts/discover.py --role attack
   python3 scripts/handoff.py --list
   # Build tools / deploy
   ```

## Environment Variables

| Variabel | Default | Keterangan |
|---|---|---|
| `PTOOLSDEXEROID_PATH` | `../Ptoolsdexeroid/` | Path ke repo Ptoolsdexeroid |
| `WINDEV_SPECIALIST_PATH` | `../windev-specialist/` | Path ke repo windev-specialist |

## Aturan Keamanan

1. **Wajib otorisasi tertulis** sebelum eksekusi kit ke target nyata
2. **Read-only** pada target data sampai operator konfirmasi
3. **Redact credentials** — gunakan `<REDACTED>`
4. **Scope gate fail-closed** — butuh `--authorized` atau `scope.txt`
=======
# MESH_INTEGRATION.md — Integrasi 3 Repo OpenCode Mesh

Dibuat 2026-10-16. Diperbarui 2026-10-17 (setup khusus Tab Termux+proot Ubuntu).

## Repo yang Diintegrasi

| Repo | Fungsi | Path (default) |
|---|---|---|
| `Ptoolsdexeroid` | 35 kit pentest/CTF/bypass | `../Ptoolsdexeroid/` |
| `windev-specialist` | Windows dev toolkit | `../windev-specialist/` |
| `opencode-mesh-v2` | Koordinasi mesh (ini) | `.` |

## Setup di Setiap Mesin

```bash
# 1. Clone semua repo
git clone https://github.com/bryanleeanito/Ptoolsdexeroid.git
git clone https://github.com/bryanleeanito/windev-specialist.git
git clone https://github.com/bryanleeanito/opencode-mesh-v2.git

# 2. Masuk ke mesh
cd opencode-mesh-v2

# 3. Register mesin
python3 scripts/register.py --name "kali-attack" --role attack --ip 192.168.1.100

# 4. Sinkron
python3 scripts/sync.py --pull
```

## Auto-sync & Presence (mesh_status.py)

Satu perintah sync + status siapa yang hidup. `--install` sekali di tiap
mesin — setelah itu semua jalan otomatis (tiap 15 menit + saat boot),
tanpa nyusun cron/manual:

```bash
# 5. Set nama mesin ini (sekali) lalu pasang auto-sync
python3 scripts/mesh_status.py --name <nama-terdaftar>
python3 scripts/mesh_status.py --install   # cron/schtasks + self-test

# Cek presence kapan saja (pull -> update -> push -> tabel)
python3 scripts/mesh_status.py

# Mode offline / tanpa git (tabel saja)
python3 scripts/mesh_status.py --local

# Lepas auto-sync
python3 scripts/mesh_status.py --uninstall
```

- presence per mesin: `state/presence/<nama>.json` (last_seen epoch UTC).
- `online` = scheduler/mesin hidup, bukan user aktif; `!` = stale > 1 jam.
- identitas mesin: `~/.mesh_self.json` (di luar repo, tidak ikut push).
- di mode cron, push presence di-rate-limit 10 menit (hemat commit);
  gagal sync dicatat ke `state/last_error.log`.

## Setup khusus: Tab via Termux + proot Ubuntu

Tab jalanin OpenCode di **proot Ubuntu (glibc, ARM64)** — platform resmi yang
didukung OpenCode (ada binary standalone `linux-arm64`). Di DALAM proot:

```bash
# 1. Dependensi
apt update && apt install -y git curl python3 unzip

# 2. OpenCode V2 (native ARM64 glibc)
curl -fsSL https://opencode.ai/v2/install | bash
#   alternatif: apt install nodejs npm && npm install -g @opencode/cli
opencode --version   # bukti terpasang

# 3. Git identity + credentials (WAJIB — mesh itu git push)
git config --global user.name "kzldx"
git config --global user.email "kzldx@users.noreply.github.com"
git config --global credential.helper store   # sekali ketik PAT, tersimpan
#   alternatif: bikin SSH key -> tambah ke akun GitHub

# 4. Masuk mesh
git clone https://github.com/bryanleeanito/opencode-mesh-v2.git ~/opencode-mesh-v2
cd ~/opencode-mesh-v2
python3 scripts/register.py --name tablet-analysis --role analysis \
  --ip "$(hostname -I | awk '{print $1}')" --capabilities osint,analysis,reporting
python3 scripts/sync.py --pull
python3 scripts/discover.py --all
```

Jebakan proot/Termux:

- **Repo di `~/`, jangan `/sdcard`** — filesystem eksternal Android = noexec
  + permission aneh, binary/script gagal jalan.
- **Push mesh butuh auth GitHub**: transport = `git push` HTTPS. Tanpa PAT
  (`credential.helper store`) atau SSH key, kamu bisa PULL tapi tidak bisa
  KIRIM pesan — mesh jadi satu arah.
- Proot tanpa systemd — OpenCode service start on-demand; kalau macet:
  `opencode service status` / `opencode service restart`, atau fallback
  `opencode --standalone`.
- Supaya sesi tidak mati saat layar off: `termux-wake-lock`.
- IP proot = IP Android (jaringan dibagikan) — `hostname -I` langsung dapat
  IP LAN yang terlihat mesin lain.
- Alur harian: `sync.py --pull` awal sesi → kerja/kirim pesan →
  `sync.py --push` sebelum tutup (commit dulu kalau ada perubahan lokal,
  lalu pull baru push).

## Cara Eksekusi Kit Lewat Mesh

### 1. Lihat semua kit
```bash
python3 scripts/mesh_integrator.py list-kits
```

### 2. Jalankan kit langsung
```bash
# Contoh: WAF bypass encode
python3 scripts/mesh_integrator.py run-kit --kit waf-bypass --command "encode --payload 'test' --method double-url"

# Contoh: Sherlock OSINT
python3 scripts/mesh_integrator.py run-kit --kit sherlock-osint --command "username --target testuser --limit 5"
```

### 3. Delegasi ke mesin lain
```bash
# Delegasi task + kit ke mesin lain
python3 scripts/mesh_integrator.py delegate-kit --to kali-attack --kit waf-bypass --command "encode --payload 'test' --method double-url"
```

## Alur Kerja Tiga Mesin

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   KALI      │    │  TABLET     │    │   WINDOWS   │
│  (Attack)   │    │  (Analysis) │    │ (Dev+DevOps)│
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │ 1. Attack        │                  │
       │    run kit       │                  │
       ▼                  │                  │
mesh_v2 <──────────────────┼──────────────────┤
       │                  │                  │
       │                  │ 2. Analysis      │
       │                  │    run kit       │
       │                  ▼                  │
       │                  │                  │
       │                  │ 3. Dev           │
       │                  │    build/deploy  │
       │                  │                  │
       └──────────────────┴──────────────────┘
       4. Share findings via mesh (share.py / broadcast.py)
```

## Contoh Kerja Sama

### Skenario: Pentest Target

1. **Kali (Attack)**:
   ```bash
   python3 scripts/mesh_integrator.py run-kit --kit waf-bypass --command "method --target target.com"
   python3 scripts/share.py --type finding --message "WAF Cloudflare detected"
   ```

2. **Tablet (Analysis)**:
   ```bash
   python3 scripts/discover.py --all
   python3 scripts/share.py --list
   python3 scripts/mesh_integrator.py run-kit --kit sherlock-osint --command "domain --target target.com"
   ```

3. **Windows (Dev/DevOps)**:
   ```bash
   python3 scripts/discover.py --role attack
   python3 scripts/handoff.py --list
   # Build tools / deploy
   ```

## Environment Variables

| Variabel | Default | Keterangan |
|---|---|---|
| `PTOOLSDEXEROID_PATH` | `../Ptoolsdexeroid/` | Path ke repo Ptoolsdexeroid |
| `WINDEV_SPECIALIST_PATH` | `../windev-specialist/` | Path ke repo windev-specialist |

## Aturan Keamanan

1. **Wajib otorisasi tertulis** sebelum eksekusi kit ke target nyata
2. **Read-only** pada target data sampai operator konfirmasi
3. **Redact credentials** — gunakan `<REDACTED>`
4. **Scope gate fail-closed** — butuh `--authorized` atau `scope.txt`
>>>>>>> e0eb6d5 (mesh-sync: 2026-10-20 00:45:02)
