"""Deploy/refresh a Remocon agent over SSH, end-to-end (Windows, Linux or macOS target).

Pushes the remocon package to ~/.remocon/app, writes the agent config (reusing
the per-machine secret if it was registered before), then runs
`remocon service install agent` *on the target*, so a deployed machine gets the
very same autostart as one set up by hand. Finally records the machine in the
hub config; the hub notices and opens the SSH tunnel itself.

Target OS is auto-detected via `uname -s` (Linux/Darwin), else Windows.

Prereq: the hub's SSH public key is authorized on the target (run the enroll
script there once — the web UI's "+ machine" dialog shows it).

Usage: remocon deploy <id> <host> <sshUser> [--python EXE] [--ssh-port N] [--winservice]
"""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys

from .. import paths
from ..config import AGENT_PORT, HUB_PORT, load_config, save_config

SSH_OPTS = ["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=12"]
LOCAL_PORTS = range(9101, 9200)


class Target:
    def __init__(self, user: str, host: str, port: int):
        self.user, self.host, self.port = user, host, port
        self.os = ""

    def ssh(self, cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(["ssh", *SSH_OPTS, "-p", str(self.port), f"{self.user}@{self.host}", cmd],
                              capture_output=True, text=True, errors="replace")

    def out(self, cmd: str) -> str:
        lines = (self.ssh(cmd).stdout or "").strip().splitlines()
        return lines[0].strip() if lines else ""

    def scp(self, src, dst: str, recursive: bool = False) -> None:
        argv = ["scp", "-q", *SSH_OPTS, "-P", str(self.port)]
        if recursive:
            argv.append("-r")
        subprocess.run([*argv, str(src), f"{self.user}@{self.host}:{dst}"], check=True)


def detect_os(t: Target) -> str:
    r = t.ssh("uname -s")
    s = (r.stdout or "").strip()
    if r.returncode == 0 and s in ("Linux", "Darwin"):
        return "linux" if s == "Linux" else "macos"
    return "windows"


def prepare(t: Target, pyexe: str | None) -> tuple[str, str, str]:
    """-> (python, claude path, home dir) on the target."""
    if t.os == "windows":
        pyexe = pyexe or t.out(
            'powershell -NoProfile -Command "(Get-Command python.exe -All -EA SilentlyContinue | '
            "Where-Object { $_.Source -notlike '*WindowsApps*' } | Select-Object -First 1).Source\"")
        if not pyexe:
            sys.exit("No real Python found on target (only the Store stub) — install Python first")
        home = t.out("echo %USERPROFILE%") or f"C:\\Users\\{t.user}"
        claude = f"{home}\\.local\\bin\\claude.exe"
        t.ssh(f'"{pyexe}" -m pip install --quiet --user pywinpty')
        t.ssh("if not exist .remocon\\app mkdir .remocon\\app")
    else:
        pyexe = pyexe or t.out("command -v python3 || command -v python")
        if not pyexe:
            sys.exit("python3 not found on target — install it first")
        home = t.out("echo $HOME") or f"/home/{t.user}"
        claude = t.out("command -v claude || echo $HOME/.local/bin/claude") or "claude"
        t.ssh("mkdir -p .remocon/app")
    return pyexe, claude, home


def install_service(t: Target, pyexe: str, home: str, winservice: bool) -> str:
    if t.os == "windows":
        app = f"{home}\\.remocon\\app"
        flag = " --winservice" if winservice else ""
        r = t.ssh(f'cd /d "{app}" && "{pyexe}" -m remocon service install agent{flag}')
    else:
        # systemctl --user over a non-login SSH session needs the runtime dir
        r = t.ssh(f'export XDG_RUNTIME_DIR=/run/user/$(id -u); cd "$HOME/.remocon/app" && '
                  f'"{pyexe}" -m remocon service install agent')
    return (r.stdout or r.stderr or "?").strip()


def deploy(mid: str, host: str, user: str, pyexe: str | None = None, ssh_port: int = 22,
           winservice: bool = False) -> dict:
    t = Target(user, host, ssh_port)
    if t.ssh("echo ok").returncode != 0:
        sys.exit(f"SSH failed: {user}@{host}:{ssh_port} — run the enroll script on the target first")

    t.os = detect_os(t)
    print("target OS:", t.os)
    pyexe, claude, home = prepare(t, pyexe)
    print("python:", pyexe)

    cfg = load_config()
    machines = cfg.setdefault("machines", [])
    entry = next((m for m in machines if m.get("id") == mid), None)
    if entry and entry.get("secret") and entry.get("localPort"):
        secret, local_port = entry["secret"], entry["localPort"]
        print(f"reusing existing registration: localPort {local_port}")
    else:
        secret = secrets.token_hex(32)
        used = {m.get("localPort") for m in machines}
        local_port = next(p for p in LOCAL_PORTS if p not in used)
        print(f"new registration: localPort {local_port}")

    # code: the whole package, same tree on every OS
    t.scp(paths.package_root() / "remocon", ".remocon/app/", recursive=True)

    # agent config: only what an agent needs; it never sees other machines
    acfg = {"secret": secret, "claudePath": claude,
            "agent": {"host": "127.0.0.1", "port": AGENT_PORT},
            "control": {"host": "127.0.0.1", "port": HUB_PORT}}
    tmp = paths.run_dir() / f"deploy-{mid}.config.json"
    tmp.write_text(json.dumps(acfg, indent=2), encoding="utf-8")
    try:
        t.scp(tmp, ".remocon/config.json")
    finally:
        tmp.unlink(missing_ok=True)

    print("service:", install_service(t, pyexe, home, winservice))

    cfg = load_config()   # re-read: the UI may have changed it meanwhile
    machines = cfg.setdefault("machines", [])
    entry = next((m for m in machines if m.get("id") == mid), None)
    if entry is None:
        entry = {"id": mid}
        machines.append(entry)
    entry.update({"name": entry.get("name", mid), "host": host, "sshUser": user, "sshPort": ssh_port,
                  "os": t.os, "agentPort": AGENT_PORT, "localPort": local_port,
                  "secret": secret, "pythonExe": pyexe, "claudePath": claude})
    save_config(cfg)
    print(f"✅ deployed '{mid}' ({user}@{host}, {t.os}) -> 127.0.0.1:{local_port}")
    return entry


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(prog="remocon deploy", description=__doc__.split("\n\n")[0])
    add_arguments(ap)
    a = ap.parse_args(argv)
    run(a)
    return 0


def add_arguments(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("id")
    ap.add_argument("host")
    ap.add_argument("ssh_user")
    ap.add_argument("--python", dest="pyexe", default=None, help="python on the target (auto-detected)")
    ap.add_argument("--ssh-port", type=int, default=22)
    ap.add_argument("--winservice", action="store_true",
                    help="Windows target: run as a Windows service (needs pywin32)")


def run(a) -> None:
    deploy(a.id, a.host, a.ssh_user, a.pyexe or None, a.ssh_port, a.winservice)


if __name__ == "__main__":
    raise SystemExit(main())
