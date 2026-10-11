"""`remocon` command line.

    remocon up                  hub + local agent in one process (the machine you browse from)
    remocon hub                 web UI + machine registry + SSH tunnels + skill sync
    remocon agent               this machine's agent (every machine runs one)
    remocon init [--import F]   write ~/.remocon/config.json (optionally from csm.config.json)
    remocon service install|uninstall|status [ROLE]   autostart at login/boot
    remocon deploy ID HOST USER push + install an agent on another machine over SSH
    remocon skills-sync         converge ~/.claude/skills across machines once
    remocon open                open the web UI in the browser
    remocon doctor              check python, claude, codex, ssh, ports, config
"""

from __future__ import annotations

import argparse
import shutil
import socket
import sys
import threading
import webbrowser

from . import __version__, paths
from .config import config_path, import_legacy, load_config, which_claude


def _redirect_headless_stdio() -> None:
    # Under pythonw.exe (no console) sys.stdout/stderr are None and any write
    # kills the process; send them to a log so services run headless cleanly.
    if sys.stdout is None or sys.stderr is None:
        log = open(paths.logs_dir() / "remocon.log", "a", buffering=1, encoding="utf-8")
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


def _hub_url(cfg: dict) -> str:
    host = cfg["control"]["host"]
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1"
    return f"http://{host}:{cfg['control']['port']}"


def cmd_agent(a) -> int:
    from .agent import server
    server.serve(load_config()).serve_forever()
    return 0


def cmd_hub(a, with_agent: bool = False) -> int:
    from .hub import server, skillsync
    cfg = load_config()
    if with_agent:
        from .agent import server as agent_server
        httpd = agent_server.serve(cfg)
        threading.Thread(target=httpd.serve_forever, daemon=True, name="agent").start()
    hub = server.serve(cfg)
    skillsync.start_loop(cfg)
    print(f"\n  ▶ Remocon: {_hub_url(cfg)}\n", file=sys.stderr)
    if getattr(a, "open", False):
        webbrowser.open(_hub_url(cfg))
    try:
        hub.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def cmd_init(a) -> int:
    p = config_path()
    if a.import_from:
        import_legacy(a.import_from)
        print(f"imported {a.import_from} -> {p}")
    elif p.exists() and not a.force:
        print(f"config already exists: {p}  (use --force to regenerate)")
    else:
        if p.exists():
            p.unlink()
        load_config()
        print(f"wrote {p}")
    return 0


def cmd_service(a) -> int:
    from .host import service
    try:
        if a.action == "install":
            print(service.install(a.role, winservice=a.winservice))
        elif a.action == "uninstall":
            print(service.uninstall(a.role))
        else:
            print(f"{a.role}: {service.status(a.role)}")
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_deploy(a) -> int:
    from .hub import deploy
    deploy.run(a)
    return 0


def cmd_skills_sync(a) -> int:
    from .hub import skillsync
    s = skillsync.sync()
    return 1 if s.get("errors") else 0


def cmd_open(a) -> int:
    webbrowser.open(_hub_url(load_config()))
    return 0


def _port_free(host: str, port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex((host, port)) != 0


def cmd_doctor(a) -> int:
    cfg = load_config()
    ok = True

    def row(good: bool, label: str, detail: str = "", required: bool = True):
        nonlocal ok
        ok = ok and (good or not required)
        mark = "✅" if good else ("❌" if required else "⚠️ ")
        print(f"{mark} {label:<14} {detail}")

    row(sys.version_info >= (3, 10), "python", sys.version.split()[0])
    row(config_path().exists(), "config", str(config_path()))
    claude = cfg.get("claudePath") or which_claude()
    row(bool(shutil.which(claude) or shutil.which("claude")), "claude", claude)
    row(bool(shutil.which("codex")), "codex", shutil.which("codex") or "not found (optional)", required=False)
    row(bool(shutil.which("ssh")), "ssh", shutil.which("ssh") or "not found — needed for remote machines")
    from .hub.enroll import hub_pubkey
    row(bool(hub_pubkey()), "ssh key", "ok" if hub_pubkey() else "none — run: ssh-keygen -t ed25519",
        required=False)
    if paths.IS_WIN:
        try:
            import winpty  # noqa: F401
            row(True, "pywinpty", "ok")
        except ImportError:
            row(False, "pywinpty", "missing — pip install pywinpty")
    for role, sect in (("agent", "agent"), ("hub", "control")):
        h, p = cfg[sect]["host"], int(cfg[sect]["port"])
        row(True, f"{role} port", f"{h}:{p} " + ("free" if _port_free(h, p) else "in use (running?)"))
    from .host import service
    for role in service.ROLES:
        print(f"   service {role:<6} {service.status(role)}")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="remocon", description="Remote control for coding-agent sessions.")
    ap.add_argument("--version", action="version", version=f"remocon {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("up", help="hub + local agent (default for the machine you browse from)")
    p.add_argument("--open", action="store_true", help="open the web UI")
    p.set_defaults(fn=lambda a: cmd_hub(a, with_agent=True))
    p = sub.add_parser("hub", help="web UI, registry, tunnels, skill sync")
    p.add_argument("--open", action="store_true", help="open the web UI")
    p.set_defaults(fn=cmd_hub)
    sub.add_parser("agent", help="this machine's agent").set_defaults(fn=cmd_agent)

    p = sub.add_parser("init", help="write ~/.remocon/config.json")
    p.add_argument("--import", dest="import_from", metavar="CSM_CONFIG",
                   help="adopt a legacy csm.config.json")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("service", help="autostart at login/boot")
    p.add_argument("action", choices=("install", "uninstall", "status"))
    p.add_argument("role", nargs="?", default="up", choices=("agent", "hub", "up"))
    p.add_argument("--winservice", action="store_true", help="Windows agent: pywin32 service")
    p.set_defaults(fn=cmd_service)

    from .hub import deploy
    p = sub.add_parser("deploy", help="install an agent on another machine over SSH")
    deploy.add_arguments(p)
    p.set_defaults(fn=cmd_deploy)

    sub.add_parser("skills-sync", help="converge ~/.claude/skills once").set_defaults(fn=cmd_skills_sync)
    sub.add_parser("open", help="open the web UI").set_defaults(fn=cmd_open)
    sub.add_parser("doctor", help="check the setup").set_defaults(fn=cmd_doctor)
    return ap


def main(argv: list | None = None) -> int:
    _redirect_headless_stdio()
    a = build_parser().parse_args(argv)
    return a.fn(a) or 0
