# MESH_INTEGRATION.md — Integrasi 3 Repo OpenCode Mesh

Dibuat 2026-10-16.

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
