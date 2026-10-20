#!/usr/bin/env bash
# mesh_bootstrap.sh — AKTIFKAN mesh OpenCode di mesin ini, satu perintah.
#
# Aman diulang (idempotent): skrip yang sudah beres tidak diulang.
#
#   bash scripts/mesh_bootstrap.sh --name windows-dev --role development \
#        --ip 192.168.2.104 --capabilities dev,devops,build,deploy,automasi
#
#   bash scripts/mesh_bootstrap.sh --name blackarch-attack --role attack \
#        --ip 192.168.1.100 --capabilities pentest,bypass,exploit --with-kits
#
# Flag:
#   --name <nama>          nama mesin di mesh (wajib)
#   --role <role>          attack|analysis|development|pentest|ctf
#   --ip <ip>              IP mesin (default: autodetect)
#   --capabilities <a,b>   daftar kapabilitas
#   --dir <path>           lokasi repo mesh (default: repo tempat skrip ini)
#   --with-kits            sekalian clone Ptoolsdexeroid + windev-specialist
#   --no-cron              jangan pasang auto-sync (presence manual saja)
#   --skip-register        jangan sentuh registry (mesin sudah terdaftar)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MESH_REPO_URL="${MESH_REPO_URL:-https://github.com/bryanleeanito/opencode-mesh-v2.git}"
PT_REPO_URL="${PT_REPO_URL:-https://github.com/bryanleeanito/Ptoolsdexeroid.git}"
WIN_REPO_URL="${WIN_REPO_URL:-https://github.com/bryanleeanito/windev-specialist.git}"

NAMA=""; ROLE=""; IP=""; CAPS=""; DIR="$REPO_DIR"; DENGAN_KITS=0; TANPA_CRON=0; SKIP_REGISTER=0

while [ $# -gt 0 ]; do
  case "$1" in
    --name) NAMA="$2"; shift 2 ;;
    --role) ROLE="$2"; shift 2 ;;
    --ip) IP="$2"; shift 2 ;;
    --capabilities) CAPS="$2"; shift 2 ;;
    --dir) DIR="$2"; shift 2 ;;
    --with-kits) DENGAN_KITS=1; shift ;;
    --no-cron) TANPA_CRON=1; shift ;;
    --skip-register) SKIP_REGISTER=1; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "[!] argumen tak dikenal: $1" >&2; exit 1 ;;
  esac
done

[ -n "$NAMA" ] || { echo "[!] --name wajib diisi" >&2; exit 1; }
[ -n "$ROLE" ] || ROLE="analysis"
if [ -z "$IP" ]; then
  IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  [ -n "$IP" ] || IP="127.0.0.1"
fi

step() { echo; echo "==> $*"; }
ok()   { echo "[OK] $*"; }
warn() { echo "[!] $*"; }
die()  { echo "[X] $*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 tidak ada di PATH"
command -v git >/dev/null 2>&1 || die "git tidak ada di PATH"

# --- 1. repo mesh ---
step "1. Repo mesh"
if [ -f "$DIR/scripts/mesh_status.py" ]; then
  ok "repo ada di $DIR"
else
  warn "repo tidak lengkap di $DIR, clone ke sana"
  git clone "$MESH_REPO_URL" "$DIR"
  ok "cloned"
fi
S="$DIR/scripts"

# --- 2. repo saudara (kit) ---
if [ "$DENGAN_KITS" = "1" ]; then
  step "2. Repo kit"
  PARENT="$(cd "$DIR/.." && pwd)"
  for spec in "Ptoolsdexeroid:$PT_REPO_URL" "windev-specialist:$WIN_REPO_URL"; do
    nama="${spec%%:*}"; url="${spec#*:}"
    if [ -d "$PARENT/$nama/.git" ]; then
      ok "$nama sudah ada"
    else
      git clone --depth 1 "$url" "$PARENT/$nama" && ok "$nama cloned"
    fi
  done
else
  step "2. Repo kit"
  warn "skip (pakai --with-kits kalau mau kit Ptoolsdexeroid/windev)"
fi

# --- 3. kredensial git (push tanpa prompt) ---
step "3. Kredensial git"
if git config --global credential.helper store >/dev/null 2>&1; then
  ok "credential.helper=store aktif"
else
  warn "credential.helper belum di-set. Mesh jadi 1 arah (bisa pull, tidak bisa kirim):"
  warn "  git config --global credential.helper store   # lalu ketik PAT sekali"
fi

# --- 4. register ---
if [ "$SKIP_REGISTER" = "1" ]; then
  step "4. Register"
  warn "skip (--skip-register)"
else
  step "4. Register mesin: $NAMA"
  python3 "$S/register.py" --name "$NAMA" --role "$ROLE" --ip "$IP" \
    ${CAPS:+--capabilities "$CAPS"}
fi

# --- 5. identitas + presence ---
step "5. Identitas mesin & presence"
python3 "$S/mesh_status.py" --name "$NAMA" --local

# --- 6. auto-sync ---
if [ "$TANPA_CRON" = "1" ]; then
  step "6. Auto-sync"
  warn "skip (--no-cron)"
else
  step "6. Auto-sync (cron + boot + self-test)"
  python3 "$S/mesh_status.py" --install
fi

# --- 7. cron daemon (Linux/proot tanpa init) ---
if [ "$TANPA_CRON" != "1" ] && [ "$(uname -s)" = "Linux" ]; then
  step "7. Cron daemon"
  if pgrep -x cron >/dev/null 2>&1; then
    ok "cron sudah jalan"
  elif [ -x /usr/sbin/cron ]; then
    /usr/sbin/cron && ok "cron dijalankan"
  else
    warn "cron tidak terpasang (apt install cron)"
  fi
  # autostart tiap login proot (tidak ada systemd)
  if [ -f "$HOME/.bashrc" ] && ! grep -q "mesh-presence: nyalakan cron daemon" "$HOME/.bashrc" 2>/dev/null; then
    cat >> "$HOME/.bashrc" <<'EOF'

# mesh-presence: nyalakan cron daemon (proot tidak punya init) - idempotent
if [ -x /usr/sbin/cron ] && ! pgrep -x cron >/dev/null 2>&1; then
  /usr/sbin/cron 2>/dev/null
fi
EOF
    ok "autostart cron ditambahkan ke ~/.bashrc"
  else
    ok "autostart cron sudah ada"
  fi
fi

# --- 8. verifikasi ---
step "8. Verifikasi"
echo "--- crontab ---"; crontab -l 2>/dev/null | grep mesh-presence || warn "entri cron tidak ada"
echo "--- cron daemon ---"; pgrep -x cron >/dev/null 2>&1 && ok "hidup" || warn "mati (jalankan: /usr/sbin/cron)"
echo "--- presence ---"; ls -1 "$DIR/state/presence/" 2>/dev/null || warn "belum ada file presence"
echo "--- push tes ---"
if git -C "$DIR" push --dry-run origin HEAD >/dev/null 2>&1; then
  ok "kredensial push OK"
else
  warn "push TIDAK bisa - mesh jadi 1 arah (fix credential GitHub)"
fi

echo
echo "=== Mesh aktif di mesin '$NAMA' ==="
python3 "$S/mesh_status.py" --local
echo
echo "Langkah berikutnya:"
echo "  python3 $S/broadcast.py --message \"halo dari $NAMA\""
echo "  python3 $S/discover.py --all"
