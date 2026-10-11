"""Run a Remocon role at login/boot and keep it running — on every OS.

    macOS    launchd user agent      ~/Library/LaunchAgents/com.remocon.<role>.plist
    Linux    systemd user service    ~/.config/systemd/user/remocon-<role>.service (+ linger)
    Windows  scheduled task          Remocon-<Role>: at logon + a 5-minute watchdog

Roles: `agent` (every machine), `hub` (web UI + tunnels + skill sync) and `up`
(both, for the machine you browse from). `remocon deploy` runs this same code on
the remote machine, so a machine set up by hand and one set up over SSH end up
identical.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .. import paths
from .proc import headless_python

ROLES = ("agent", "hub", "up")
IS_WIN = os.name == "nt"


def _label(role: str) -> str:
    return f"com.remocon.{role}"


def _unit(role: str) -> str:
    return f"remocon-{role}"


def _task(role: str) -> str:
    return f"Remocon-{role.capitalize()}"


def _extra_path() -> str:
    h = Path.home()
    return os.pathsep.join(str(p) for p in (h / ".local" / "bin", "/opt/homebrew/bin", "/usr/local/bin"))


def _argv(role: str, headless: bool = False) -> list:
    return [headless_python() if headless else sys.executable, "-m", "remocon", role]


def _run(argv, **kw):
    return subprocess.run(argv, capture_output=True, text=True, errors="replace", **kw)


# ---- macOS ------------------------------------------------------------------

def _plist_path(role: str) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{_label(role)}.plist"


def render_plist(role: str) -> str:
    from xml.sax.saxutils import escape as e
    args = "".join(f"\n    <string>{e(a)}</string>" for a in _argv(role))
    log = paths.logs_dir() / f"{role}.log"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{_label(role)}</string>
  <key>ProgramArguments</key>
  <array>{args}
  </array>
  <key>WorkingDirectory</key><string>{e(str(paths.home()))}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONPATH</key><string>{e(str(paths.package_root()))}</string>
    <key>PATH</key><string>{e(_extra_path())}:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{e(str(log))}</string>
  <key>StandardErrorPath</key><string>{e(str(log))}</string>
</dict>
</plist>
"""


def _mac_install(role: str) -> str:
    p = _plist_path(role)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_plist(role), encoding="utf-8")
    dom = f"gui/{os.getuid()}"
    _run(["launchctl", "bootout", f"{dom}/{_label(role)}"])
    r = _run(["launchctl", "bootstrap", dom, str(p)])
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "launchctl bootstrap failed")
    return f"launchd: {p}"


def _mac_uninstall(role: str) -> str:
    _run(["launchctl", "bootout", f"gui/{os.getuid()}/{_label(role)}"])
    _plist_path(role).unlink(missing_ok=True)
    return "launchd job removed"


def _mac_status(role: str) -> str:
    r = _run(["launchctl", "print", f"gui/{os.getuid()}/{_label(role)}"])
    if r.returncode != 0:
        return "not installed"
    state = next((l.strip() for l in r.stdout.splitlines() if l.strip().startswith("state =")), "")
    return state or "installed"


# ---- Linux ------------------------------------------------------------------

def _unit_path(role: str) -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "systemd" / "user" / f"{_unit(role)}.service"


def render_unit(role: str) -> str:
    cmd = " ".join(f'"{a}"' if " " in a else a for a in _argv(role))
    return (
        "[Unit]\n"
        f"Description=Remocon {role}\n"
        "After=network-online.target\n\n"
        "[Service]\n"
        f"ExecStart={cmd}\n"
        f"WorkingDirectory={paths.home()}\n"
        f"Environment=PYTHONPATH={paths.package_root()}\n"
        f"Environment=PATH={_extra_path()}:/usr/bin:/bin\n"
        "Restart=always\n"
        "RestartSec=10\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def _linux_install(role: str) -> str:
    p = _unit_path(role)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_unit(role), encoding="utf-8")
    # linger: start at boot, keep running after the SSH session that set it up ends
    _run(["loginctl", "enable-linger", os.environ.get("USER", "")])
    _run(["systemctl", "--user", "daemon-reload"])
    r = _run(["systemctl", "--user", "enable", "--now", _unit(role)])
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "systemctl enable failed")
    _run(["systemctl", "--user", "restart", _unit(role)])
    return f"systemd: {p}"


def _linux_uninstall(role: str) -> str:
    _run(["systemctl", "--user", "disable", "--now", _unit(role)])
    _unit_path(role).unlink(missing_ok=True)
    _run(["systemctl", "--user", "daemon-reload"])
    return "systemd unit removed"


def _linux_status(role: str) -> str:
    r = _run(["systemctl", "--user", "is-active", _unit(role)])
    return (r.stdout or r.stderr).strip() or "unknown"


# ---- Windows ----------------------------------------------------------------

def _ps(script: str) -> subprocess.CompletedProcess:
    return _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])


def _win_install(role: str) -> str:
    # wscript runs pythonw hidden and waits on it, so the task stays "Running"
    # while the role lives; IgnoreNew turns the 5-minute repeat into a watchdog
    # that only fires once the process has died.
    argv = _argv(role, headless=True)
    cmdline = " ".join(f'""{a}""' for a in argv)
    vbs = paths.run_dir() / f"{role}.vbs"
    vbs.write_text(
        'Set sh = CreateObject("WScript.Shell")\r\n'
        f'sh.Environment("PROCESS")("PYTHONPATH") = "{paths.package_root()}"\r\n'
        f'sh.CurrentDirectory = "{paths.home()}"\r\n'
        f'sh.Run "{cmdline}", 0, True\r\n', encoding="utf-8")
    name = _task(role)
    r = _ps(
        f"$a=New-ScheduledTaskAction -Execute 'wscript.exe' -Argument '\"{vbs}\"';"
        "$t=@((New-ScheduledTaskTrigger -AtLogOn),"
        "(New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)));"
        "$s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 "
        "-RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
        "-MultipleInstances IgnoreNew;"
        f"Register-ScheduledTask -TaskName '{name}' -Action $a -Trigger $t -Settings $s -Force | Out-Null;"
        f"Stop-ScheduledTask -TaskName '{name}' -EA SilentlyContinue; Start-Sleep 1;"
        f"Start-ScheduledTask -TaskName '{name}'")
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "Register-ScheduledTask failed")
    return f"scheduled task: {name}"


WINSVC = "Remocon-Agent"


def _win_service(role: str) -> str:
    """Install/refresh the pywin32 service; return the account it logs on as.

    `update` keeps the logon account, so a password set once in services.msc
    survives redeploys. Only the agent role runs as a service.
    """
    py = sys.executable
    pydir = os.path.dirname(py)
    svc = Path(__file__).resolve().parent / "winservice.py"
    r = _ps(
        f"$py='{py}'; $svc='{svc}';"
        f"$verb = if (Get-Service {WINSVC} -EA SilentlyContinue) {{ 'update' }} else {{ 'install' }};"
        "& $py $svc --startup auto $verb | Out-Null;"
        # pythonservice.exe gets only the system environment; let it find python3xx.dll + pywintypes.
        f"Set-ItemProperty HKLM:\\SYSTEM\\CurrentControlSet\\Services\\{WINSVC} -Name Environment "
        f"-Type MultiString -Value @('PATH={pydir};{pydir}\\Lib\\site-packages\\pywin32_system32;"
        "C:\\Windows\\system32;C:\\Windows');"
        f"sc.exe failure {WINSVC} reset= 86400 actions= restart/60000/restart/60000/restart/60000 | Out-Null;"
        f"Write-Host ('ACCOUNT='+(Get-CimInstance Win32_Service -Filter \"Name='{WINSVC}'\").StartName)")
    return next((l[8:].strip() for l in r.stdout.splitlines() if l.startswith("ACCOUNT=")), "")


def _win_install_service(role: str) -> str:
    try:
        import win32serviceutil  # noqa: F401  (pywin32)
    except ImportError:
        return _win_install(role) + "  (pywin32 missing: pip install pywin32 for the service)"
    acct = _win_service(role)
    if acct and acct.lower() != "localsystem":
        # The service runs as the user and owns the agent; retire the logon
        # task so the two never both bind the port.
        _win_uninstall(role)
        _ps(f"Stop-Service {WINSVC} -Force -EA SilentlyContinue; Start-Sleep 1; Start-Service {WINSVC}")
        return f"windows service: {WINSVC} (as {acct})"
    # The service can't log on as the user until their password is set
    # (services.msc → Remocon-Agent → Log On): use the logon task meanwhile and
    # install again once the password is in. Left on Automatic, it would start
    # at boot as LocalSystem — the wrong home, no claude login — and take the
    # port before the task does, so it waits on Manual until then.
    _ps(f"Stop-Service {WINSVC} -Force -EA SilentlyContinue; Set-Service {WINSVC} -StartupType Manual")
    return (_win_install(role) + f"  ({WINSVC} service installed but logs on as LocalSystem — set the "
            "user's password in services.msc → Log On, then run this again to switch over)")


def _win_uninstall(role: str) -> str:
    name = _task(role)
    _ps(f"Stop-ScheduledTask -TaskName '{name}' -EA SilentlyContinue;"
        f"Unregister-ScheduledTask -TaskName '{name}' -Confirm:$false -EA SilentlyContinue")
    return "scheduled task removed"


def _win_status(role: str) -> str:
    r = _ps(f"(Get-ScheduledTask -TaskName '{_task(role)}' -EA SilentlyContinue).State")
    return r.stdout.strip() or "not installed"


# ---- dispatch ---------------------------------------------------------------

def _impl(kind: str):
    plat = "win" if IS_WIN else ("mac" if sys.platform == "darwin" else "linux")
    return globals()[f"_{plat}_{kind}"]


def install(role: str, winservice: bool = False) -> str:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    paths.home().mkdir(parents=True, exist_ok=True)
    if IS_WIN and winservice and role == "agent":
        return _win_install_service(role)
    return _impl("install")(role)


def uninstall(role: str) -> str:
    return _impl("uninstall")(role)


def status(role: str) -> str:
    return _impl("status")(role)
