"""Where Remocon keeps its own files — the same layout on every OS.

Everything lives under one directory, ~/.remocon (override with REMOCON_HOME),
so a machine set up over SSH looks exactly like one set up by hand, whether it
runs Windows, macOS or Linux:

    ~/.remocon/config.json   shared secret, ports, machine registry, UI prefs
    ~/.remocon/logs/         agent / hub / deploy / launch logs
    ~/.remocon/run/          scratch files (generated scripts, unit files)
    ~/.remocon/uploads/      images attached to codex runs
    ~/.remocon/manager/      cwd of the orchestration manager session
    ~/.remocon/app/          agent code pushed by `remocon deploy`
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

IS_WIN = os.name == "nt"


def home() -> Path:
    return Path(os.environ.get("REMOCON_HOME") or (Path.home() / ".remocon"))


def _dir(name: str) -> Path:
    p = home() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_file() -> Path:
    return Path(os.environ.get("REMOCON_CONFIG") or (home() / "config.json"))


def logs_dir() -> Path:
    return _dir("logs")


def run_dir() -> Path:
    return _dir("run")


def uploads_dir() -> Path:
    return _dir("uploads")


def manager_dir() -> Path:
    return _dir("manager")


def app_dir() -> Path:
    return home() / "app"


def package_root() -> Path:
    """The directory that holds the `remocon` package (what goes on PYTHONPATH)."""
    return Path(__file__).resolve().parent.parent


def adopt_legacy(new: Path, *old: Path) -> Path:
    """Return `new`, first copying the newest existing legacy file into place.

    The legacy csm layout kept this state under `.csm-*` names; copying (not
    moving) them keeps both tools usable side by side during a migration.
    """
    if not new.exists():
        for o in old:
            if o.exists():
                try:
                    new.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(o, new)
                except OSError:
                    pass
                break
    return new
