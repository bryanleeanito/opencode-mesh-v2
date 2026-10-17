# OpenCode Mesh V2

Dynamic mesh framework — N mesin OpenCode kolaborasi (bukan hardcode 3).
Setiap OpenCode instance (termasuk milik temen) run script ini → auto-join jaringan.

Dibuat 2026-10-16.

## Arsitektur

```
┌─────────────────────────────────────────────────────┐
│            OPENCOD MESH V2 (Dynamic N)               │
│                                                      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│  │  Kali  │ │ Tablet │ │Windows │ │Temanmu │  +... │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘       │
│      │          │          │          │             │
│      └──────────┴──────────┼──────────┘             │
│                           ▼                        │
│                ┌─────────────────┐                  │
│                │  Mesh Registry  │                  │
│                │  (auto-discover)│                  │
│                └─────────────────┘                  │
│                           ▼                        │
│                ┌─────────────────┐                  │
│                │  Broadcast Bus  │                  │
│                │  (git + pubsub) │                  │
│                └─────────────────┘                  │
└─────────────────────────────────────────────────────┘
```

## Quick Start (WAJIB di setiap mesin)

```bash
# 1. Clone repo
git clone https://github.com/bryanleeanito/opencode-mesh-v2.git
cd opencode-mesh-v2

# 2. Register mesin ini ke mesh
python3 scripts/register.py --name "kali-laptop" --role attack --ip 192.168.1.100

# 3. Pull registry dari mesin lain
python3 scripts/discover.py --all

# 4. Sinkron state
python3 scripts/sync.py --pull
```

## Scripts

| Script | Fungsi |
|---|---|
| `register.py` | Daftar mesin ini ke mesh |
| `discover.py` | Lihat semua mesin online |
| `broadcast.py` | Kirim pesan ke semua mesin |
| `subscribe.py` | Follow topik (security, dev, osint) |
| `handoff.py` | Alihkan task ke mesin lain |
| `delegate.py` | Delegasi task |
| `share.py` | Share findings/clues |
| `ideas.py` | Tukar pikiran |
| `sync.py` | Sinkronisasi state |
| `mesh_status.py` | Presence + sinkron otomatis (cron/schtasks) |

## Contoh Pemakaian

### Register + Discover

```bash
# Di Kali
python3 scripts/register.py --name "kali-attack" --role attack --ip 192.168.1.100

# Di Tablet
python3 scripts/register.py --name "tablet-analysis" --role analysis --ip 192.168.1.101

# Di Windows
python3 scripts/register.py --name "windows-dev" --role development --ip 192.168.1.102

# Di PC teman
python3 scripts/register.py --name "teman-pc" --role analysis --ip 192.168.1.103

# Lihat semua
python3 scripts/discover.py --all
```

### Broadcast (Tukar Pikiran)

```bash
# Kirim ke semua mesin
python3 scripts/broadcast.py --message "Target pakai Cloudflare, perlu bypass"

# Follow topik
python3 scripts/subscribe.py --topic security
python3 scripts/subscribe.py --topic devops
```

### Delegate Task

```bash
# Kirim task ke mesin specific
python3 scripts/delegate.py --to kali-attack --task "bypass WAF target.com"

# Kirim ke semua (broadcast)
python3 scripts/delegate.py --to all --task "laporan mingguan"
```

### Handoff

```bash
# Alihkan task ke mesin lain
python3 scripts/handoff.py --to tablet-analysis --task "analisa findings SQLi"

# Terima handoff
python3 scripts/handoff.py --list
```

## Role & Capability

| Role | Capability | Kit |
|---|---|---|
| `attack` | pentest, bypass, exploit, payload | waf-bypass, sqli-helper |
| `analysis` | osint, analysis, source_review, reporting | sherlock-osint, code-audit |
| `development` | dev, devops, build, deploy, automasi | windev-specialist |
| `pentest` | full pentest suite | Ptoolsdexeroid |
| `ctf` | CTF competition | ctf-decoder, ctf-crypto |

## State Management

```
state/
  presence/          <- presence per mesin (mesh_status.py)
  last_error.log     <- audit gagal sync (ditulis mode cron)
  registry.json      — daftar mesin online
  tasks.json         — antrian task
  findings.json      — kumpulan temuan
  ideas.json         — tukar pikiran
  subscriptions.json — topik yang di-follow
  status.json        — status tiap mesin
```

## Aturan

1. **Pull before push** — selalu `sync.py --pull` sebelum `--push`.
2. **No secrets** — credentials di env var, jangan di state file.
3. **Redact output** — sensitive data di-redact.
4. **Naming convention** — `[role]-[hostname]`.
5. **Auto-register** — mesin baru langsung join, no manual approval.

## Changelog

- **2026-10-16** — repo dibuat, dynamic mesh v2.
- **2026-10-17** — FIX BUS: `state/` ikut di-track (sebelumnya gitignored
  → broadcast/ideas/registry tak pernah sampai antar mesin); semua
  `os.uname()` → `platform.node()` (script crash di Windows); `sync --push`
  anggun saat clean. E2E 2 mesin via git terbukti (broadcast 2 arah +
  ideas + registry).
- **2026-10-17** (`a8255f5`) — TAMBAH `mesh_status.py`: presence per mesin
  (`state/presence/<nama>.json`, epoch UTC) + sinkron otomatis, mode
  `--local`/`--cron`/`--name`/`--install`/`--uninstall`/`--status`
  (`--install`: cron */15 + @reboot / schtasks `MeshPresence` +
  `MeshPresenceBoot` + self-test, rate-limit push 600 detik, push retry
  3x, `GIT_TERMINAL_PROMPT=0`). Identitas mesin di `~/.mesh_self.json`
  (di luar repo; override env `MESH_SELF_FILE`/`MESH_STATE_DIR`). Tes
  terisolasi (clone temp — tidak lagi menulis bus asli), +6 tes jadi
  16/16; FIX `mesh_integrator.py` baris 64 (`for k`→`for w`, NameError);
  README + `MESH_INTEGRATION.md` diperbarui.
