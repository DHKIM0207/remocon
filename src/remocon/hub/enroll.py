"""One-time scripts a new machine runs so the hub can reach it over SSH.

The user copies one into an (elevated) shell on the new machine: it installs
and starts an OpenSSH server, authorizes the hub's public key and checks for
Python. After that, everything else — code push, config, autostart — is
`remocon deploy` over SSH.
"""

from __future__ import annotations

from pathlib import Path

# PowerShell run (elevated) on a new Windows machine to authorize this mac + prep.
_ENROLL_PS1 = r"""# Remocon enroll — run in an ELEVATED PowerShell on the NEW machine
$ErrorActionPreference='Continue'
$key='__PUBKEY__'
Write-Host '== OpenSSH Server =='
Get-WindowsCapability -Online -Name OpenSSH.Server* 2>$null | Where-Object State -ne Installed | ForEach-Object { Add-WindowsCapability -Online -Name $_.Name | Out-Null }
Set-Service sshd -StartupType Automatic -EA SilentlyContinue; Start-Service sshd -EA SilentlyContinue
Write-Host '== authorize hub key =='
$f="$env:ProgramData\ssh\administrators_authorized_keys"
if(!(Test-Path $f)){ New-Item -ItemType File -Force -Path $f | Out-Null }
if(-not (Select-String -Path $f -SimpleMatch $key -Quiet)){ Add-Content -Path $f -Value $key -Encoding ascii }
icacls $f /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F" | Out-Null
Write-Host '== python check =='
$py=(Get-Command python.exe -All -EA SilentlyContinue | Where-Object { $_.Source -notlike '*WindowsApps*' } | Select-Object -First 1).Source
if($py){ Write-Host "python OK: $py" } else { Write-Host 'WARNING: real Python not found — install from https://python.org first' }
$ip=(Get-NetIPAddress -AddressFamily IPv4 -EA SilentlyContinue | Where-Object { $_.IPAddress -like '100.*' } | Select-Object -First 1).IPAddress
Write-Host ''
Write-Host "DONE  tailnetIP=$ip  hostname=$env:COMPUTERNAME"
Write-Host 'Now register this machine in the web UI (Add machine).'
"""

# Bash run on a new LINUX machine (sudo prompts) to authorize this host + prep.
_ENROLL_SH = r"""# Remocon enroll — run on the NEW Linux machine (sudo will prompt)
key='__PUBKEY__'
echo '== OpenSSH server =='
if command -v apt-get >/dev/null 2>&1; then sudo apt-get update -qq && sudo apt-get install -y openssh-server >/dev/null
elif command -v dnf >/dev/null 2>&1; then sudo dnf install -y openssh-server >/dev/null
elif command -v pacman >/dev/null 2>&1; then sudo pacman -S --noconfirm openssh >/dev/null; fi
sudo systemctl enable --now ssh 2>/dev/null || sudo systemctl enable --now sshd 2>/dev/null || true
echo '== authorize control host key =='
mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
grep -qF "$key" "$HOME/.ssh/authorized_keys" 2>/dev/null || echo "$key" >> "$HOME/.ssh/authorized_keys"
chmod 600 "$HOME/.ssh/authorized_keys"
echo '== python check =='
command -v python3 >/dev/null 2>&1 && echo "python3 OK: $(command -v python3)" || echo 'WARNING: python3 missing — apt/dnf install python3'
ip=$(ip -4 addr 2>/dev/null | grep -oE '100\.[0-9.]+' | head -1)
echo ''
echo "DONE  tailnetIP=${ip:-?}  hostname=$(hostname)  user=$USER"
echo 'Now register this machine in the web UI (Add machine) — deploy auto-detects Linux.'
"""


# macOS: Remote Login is the OpenSSH server; it can't be enabled from a script
# without Full Disk Access, so the script says where the switch is instead.
_ENROLL_MAC = r"""# Remocon enroll — run on the NEW Mac
key='__PUBKEY__'
echo '== Remote Login (SSH) =='
sudo systemsetup -getremotelogin 2>/dev/null || true
echo 'If it says Off: System Settings > General > Sharing > Remote Login → On'
echo '== authorize hub key =='
mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
grep -qF "$key" "$HOME/.ssh/authorized_keys" 2>/dev/null || echo "$key" >> "$HOME/.ssh/authorized_keys"
chmod 600 "$HOME/.ssh/authorized_keys"
echo '== python check =='
command -v python3 >/dev/null 2>&1 && echo "python3 OK: $(command -v python3)" || echo 'WARNING: python3 missing — xcode-select --install'
echo ''
echo "DONE  hostname=$(hostname)  user=$USER"
echo 'Now register this machine in the web UI (Add machine).'
"""

TEMPLATES = {"windows": _ENROLL_PS1, "linux": _ENROLL_SH, "macos": _ENROLL_MAC}


def hub_pubkey() -> str | None:
    for name in ("id_ed25519.pub", "id_ecdsa.pub", "id_rsa.pub"):
        f = Path.home() / ".ssh" / name
        if f.is_file():
            return f.read_text(encoding="utf-8").strip()
    return None


def script_for(target_os: str) -> str | None:
    pub = hub_pubkey()
    if not pub:
        return None
    return TEMPLATES.get(target_os, _ENROLL_PS1).replace("__PUBKEY__", pub)
