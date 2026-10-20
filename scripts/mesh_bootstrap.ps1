<#
.SYNOPSIS
    Aktifkan OpenCode Mesh di mesin Windows, satu perintah.

.DESCRIPTION
    Aman diulang (idempotent). Auto-sync dipasang lewat schtasks
    (MeshPresence tiap 15 menit + MeshPresenceBoot saat logon).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File mesh_bootstrap.ps1 -Name windows-dev -Role development -Ip 192.168.2.104 -Capabilities dev,devops,build,deploy,automasi

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File mesh_bootstrap.ps1 -Name blackarch-wsl -Role attack -Ip 192.168.1.100 -WithKits
#>
param(
    [Parameter(Mandatory = $true)][string]$Name,
    [string]$Role = "development",
    [string]$Ip = "",
    [string]$Capabilities = "",
    [string]$Dir = "",
    [switch]$WithKits,
    [switch]$NoCron,
    [switch]$SkipRegister
)

$ErrorActionPreference = "Stop"

$MeshRepoUrl = if ($env:MESH_REPO_URL) { $env:MESH_REPO_URL } else { "https://github.com/bryanleeanito/opencode-mesh-v2.git" }
$PtRepoUrl   = if ($env:PT_REPO_URL)   { $env:PT_REPO_URL }   else { "https://github.com/bryanleeanito/Ptoolsdexeroid.git" }
$WinRepoUrl  = if ($env:WIN_REPO_URL)  { $env:WIN_REPO_URL }  else { "https://github.com/bryanleeanito/windev-specialist.git" }

function Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[OK] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[!] $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "[X] $m" -ForegroundColor Red; exit 1 }

if (-not $Dir) {
    $here = Split-Path -Parent $MyInvocation.MyCommand.Path
    $Dir  = Split-Path -Parent $here
}
if (-not $Ip) {
    try { $Ip = (Get-NetIPAddress -AddressFamily IPv4 |
                 Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254*" } |
                 Select-Object -First 1 -ExpandProperty IPAddress) } catch { $Ip = "127.0.0.1" }
    if (-not $Ip) { $Ip = "127.0.0.1" }
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Die "python tidak ada di PATH" }
if (-not (Get-Command git   -ErrorAction SilentlyContinue)) { Die "git tidak ada di PATH" }

# --- 1. repo mesh ---
Step "1. Repo mesh"
if (Test-Path (Join-Path $Dir "scripts\mesh_status.py")) {
    Ok "repo ada di $Dir"
} else {
    Warn "repo tidak lengkap, clone ke $Dir"
    git clone $MeshRepoUrl $Dir
    Ok "cloned"
}
$S = Join-Path $Dir "scripts"

# --- 2. repo kit ---
Step "2. Repo kit"
if ($WithKits) {
    $parent = Split-Path -Parent $Dir
    foreach ($spec in @(@{n="Ptoolsdexeroid";u=$PtRepoUrl}, @{n="windev-specialist";u=$WinRepoUrl})) {
        $target = Join-Path $parent $spec.n
        if (Test-Path (Join-Path $target ".git")) {
            Ok "$($spec.n) sudah ada"
        } else {
            git clone --depth 1 $spec.u $target | Out-Null
            Ok "$($spec.n) cloned"
        }
    }
} else {
    Warn "skip (pakai -WithKits kalau mau kit Ptoolsdexeroid/windev)"
}

# --- 3. kredensial git ---
Step "3. Kredensial git"
$helper = (git config --global credential.helper 2>$null)
if ($helper -eq "store") {
    Ok "credential.helper=store aktif"
} else {
    Warn "credential.helper belum di-set -> mesh 1 arah (bisa pull, tidak bisa kirim)"
    Warn "  git config --global credential.helper store   # lalu ketik PAT sekali"
}

# --- 4. register ---
if ($SkipRegister) {
    Step "4. Register"; Warn "skip (-SkipRegister)"
} else {
    Step "4. Register mesin: $Name"
    $args = @((Join-Path $S "register.py"), "--name", $Name, "--role", $Role, "--ip", $Ip)
    if ($Capabilities) { $args += @("--capabilities", $Capabilities) }
    python @args
}

# --- 5. identitas + presence ---
Step "5. Identitas mesin & presence"
python (Join-Path $S "mesh_status.py") --name $Name --local

# --- 6. auto-sync (schtasks) ---
if ($NoCron) {
    Step "6. Auto-sync"; Warn "skip (-NoCron)"
} else {
    Step "6. Auto-sync (schtasks MeshPresence + MeshPresenceBoot + self-test)"
    python (Join-Path $S "mesh_status.py") --install
}

# --- 7. verifikasi ---
Step "7. Verifikasi"
Write-Host "--- scheduled task ---"
$task = schtasks /Query /TN "MeshPresence" 2>$null
if ($LASTEXITCODE -eq 0) { Ok "MeshPresence terdaftar" } else { Warn "MeshPresence tidak ada" }
Write-Host "--- presence ---"
$pres = Get-ChildItem (Join-Path $Dir "state\presence") -ErrorAction SilentlyContinue
if ($pres) { $pres | ForEach-Object { Write-Host "    $($_.Name)" } } else { Warn "belum ada file presence" }
Write-Host "--- push tes ---"
git -C $Dir push --dry-run origin HEAD *> $null
if ($LASTEXITCODE -eq 0) { Ok "kredensial push OK" } else { Warn "push TIDAK bisa - mesh 1 arah" }

Write-Host "`n=== Mesh aktif di mesin '$Name' ===" -ForegroundColor Green
python (Join-Path $S "mesh_status.py") --local
Write-Host "`nLangkah berikutnya:"
Write-Host "  python $S\broadcast.py --message `"halo dari $Name`""
Write-Host "  python $S\discover.py --all"
