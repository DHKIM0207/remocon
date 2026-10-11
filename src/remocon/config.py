"""Config loading, bootstrapping and migration.

The config file (~/.remocon/config.json, or $REMOCON_CONFIG) holds the shared
bearer secret, the agent + hub bind addresses, the path to claude, UI prefs and
the machine registry. The first load writes one with a random secret and only
this machine in it. The keys match the legacy csm.config.json, so
`remocon init --import <csm.config.json>` carries an existing setup over as is.
"""

from __future__ import annotations

import json
import os
import platform
import secrets
import shutil
import socket
from pathlib import Path

from . import paths

AGENT_PORT = 8766
HUB_PORT = 8765


def os_name() -> str:
    s = platform.system().lower()
    return {"darwin": "macos", "windows": "windows", "linux": "linux"}.get(s, s)


def which_claude() -> str:
    exe = "claude.exe" if paths.IS_WIN else "claude"
    return shutil.which("claude") or str(Path.home() / ".local" / "bin" / exe)


def config_path() -> Path:
    return paths.config_file()


def load_config() -> dict:
    p = config_path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    cfg = bootstrap()
    save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    """Write atomically, so a crash mid-write never leaves a half config behind
    (the hub re-reads it on every registry request)."""
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not paths.IS_WIN:
        os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def bootstrap() -> dict:
    return {
        "secret": secrets.token_hex(32),
        "claudePath": which_claude(),
        "selfId": "local",
        "selfName": socket.gethostname().split(".")[0],
        "agent": {"host": "127.0.0.1", "port": AGENT_PORT},
        "control": {"host": "127.0.0.1", "port": HUB_PORT},
        "skillSync": {"intervalMin": 10},
        # Registered remote machines. Each: {id, name, host, sshUser, sshPort,
        # os, agentPort, localPort, secret, pythonExe, claudePath}. Added from
        # the web UI ("+ machine") or `remocon deploy`.
        "machines": [],
    }


def import_legacy(src: Path) -> dict:
    """Adopt a legacy csm.config.json: same secret, machines,
    prefs and ports, so registered agents keep authenticating."""
    old = json.loads(Path(src).read_text(encoding="utf-8"))
    cfg = bootstrap()
    for k in ("secret", "claudePath", "selfId", "selfName", "selfSshUser",
              "agent", "control", "machines", "ui", "logDir"):
        if k in old:
            cfg[k] = old[k]
    save_config(cfg)
    return cfg
