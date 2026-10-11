"""Open a visible terminal window on this machine running one command.

Used for the codex TUI handoff: the window has to appear on whichever PC the
browser is on, so both the hub (when the browser is on the hub machine) and
every agent (when it is on a remote PC) call this.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

from .. import paths

IS_WIN = os.name == "nt"
LINUX_TERMS = ("x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal",
               "kitty", "alacritty", "xterm")


def _script(suffix: str, text: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, prefix="remocon-term-", delete=False,
                                    dir=paths.run_dir(), encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


def open_terminal(cmd: str) -> dict:
    cmd = (cmd or "").strip()
    if not cmd:
        return {"ok": False, "error": "cmd required"}
    try:
        if IS_WIN:
            # A .bat keeps the quoting in `cmd` (ssh -t "...") intact. Prefer
            # Windows Terminal, fall back to a classic console.
            bat = _script(".bat", "@echo off\r\n" + cmd + "\r\n")
            if shutil.which("wt"):
                subprocess.Popen(["wt", "new-tab", "--title", "Remocon", "cmd", "/k", bat])
            else:
                subprocess.Popen('start "Remocon" "%s"' % bat, shell=True)
        elif sys.platform == "darwin":
            f = _script(".command", '#!/bin/zsh -l\nexport PATH="$HOME/.local/bin:$PATH"\nclear\n'
                        + cmd + "\n")
            os.chmod(f, 0o755)
            app = os.environ.get("REMOCON_TERMINAL_APP") or "Terminal"
            subprocess.run(["open", "-a", app, f], capture_output=True, timeout=10)
        else:
            term = os.environ.get("REMOCON_TERMINAL") or next(
                (c for c in LINUX_TERMS if shutil.which(c)), None)
            if not term:
                return {"ok": False, "error": "no desktop terminal on this machine", "cmd": cmd}
            inner = f"{cmd}; exec bash"
            if term in ("xterm", "konsole", "alacritty"):
                argv = [term, "-e", "bash", "-lc", inner]
            elif term == "xfce4-terminal":
                argv = [term, "-x", "bash", "-lc", inner]
            elif term == "kitty":
                argv = [term, "bash", "-lc", inner]
            else:
                argv = [term, "--", "bash", "-lc", inner]
            subprocess.Popen(argv, start_new_session=True)
    except Exception as e:
        return {"ok": False, "error": str(e), "cmd": cmd}
    return {"ok": True}
