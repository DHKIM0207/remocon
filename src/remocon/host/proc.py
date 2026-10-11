"""Spawning processes that outlive whoever started them, on any OS."""

from __future__ import annotations

import os
import subprocess
import sys

IS_WIN = os.name == "nt"


def detached_kwargs() -> dict:
    """Popen kwargs for a child that survives the agent/SSH session and, on
    Windows, never flashes a console window."""
    if IS_WIN:
        return {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def headless_python() -> str:
    """pythonw.exe on Windows (no console window), the running interpreter elsewhere."""
    exe = sys.executable
    if IS_WIN and exe.lower().endswith("python.exe"):
        pyw = exe[: -len("python.exe")] + "pythonw.exe"
        if os.path.exists(pyw):
            return pyw
    return exe


def spawn_detached(argv: list, log_path) -> subprocess.Popen:
    log = open(log_path, "wb")
    return subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                            close_fds=True, **detached_kwargs())
