"""Windows ConPTY supervisor for one `claude --remote-control` launch.

The POSIX path uses pty.fork(); Windows has no fork, so we drive a real
pseudo-console via pywinpty. Spawned detached by the agent (DETACHED_PROCESS),
this process owns the ConPTY for the session's lifetime, auto-confirms the
one-time "trust this folder" prompt, then drains output until Claude exits.
The agent discovers the session via ~/.claude/sessions/<pid>.json (it does not
read anything back from here).

Usage:
    python launcher_win.py <folder> <name> <resume_id|''> <0|1 fork> <claude_path>
"""
import os
import re
import sys
import threading
import time

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

# The picker's highlight marker: plain ">" on a Windows console, ❯ elsewhere.
POINTERS = ("\u276f", "\u203a", "\u25b6", ">")
# Prompts claude puts in front of a session that nobody is sitting at. Each is
# (text that identifies the prompt, the option we answer with). Answering the
# folder-trust prompt already commits to running here, so the import prompt —
# which only asks whether the CLAUDE.md files of that same trusted folder may
# be read — is not a wider decision than the one already made.
PROMPTS = (
    ("quicksafetycheck", "yes,itrustthisfolder"),
    ("allowexternalclaude.mdfileimports", "yes,allowexternalimports"),
)


def _wanted_option(norm):
    """The option to land on, for whichever known prompt is on screen."""
    for needle, want in PROMPTS:
        if needle in norm and norm.rfind(want) != -1:
            return want
    return None


def _needs_down(norm):
    """Whether to move the highlight before pressing Enter.

    Newer claude highlights the refusing option first, so a bare Enter quits or
    declines. The marker is read from the character immediately before the
    option label rather than the last marker on screen, because
    escape-sequence leftovers can strand a stray ">".
    """
    want = _wanted_option(norm)
    if want is None:
        return False          # unknown prompt: leave the old bare Enter alone
    j = norm.rfind(want)
    return not (j and norm[j - 1] in POINTERS)


def main() -> int:
    try:  # keep the token log readable whatever the console codepage is
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    folder = os.path.realpath(os.path.expanduser(sys.argv[1]))
    name = sys.argv[2]
    resume_id = sys.argv[3]
    fork = sys.argv[4] == "1"
    claude_path = sys.argv[5]
    prompt = sys.argv[6] if len(sys.argv) > 6 else ""
    model = sys.argv[7] if len(sys.argv) > 7 else ""
    effort = sys.argv[8] if len(sys.argv) > 8 else ""
    config_dir = sys.argv[9] if len(sys.argv) > 9 else ""

    if not os.path.isdir(folder):
        sys.stderr.write(f"launcher_win: folder not found: {folder}\n")
        return 2

    argv = [claude_path, "--remote-control", name]
    if model:
        argv += ["--model", model]
    if effort:
        argv += ["--effort", effort]
    if resume_id:
        argv += ["-r", resume_id]
        if fork:
            argv += ["--fork-session"]

    from winpty import PtyProcess

    # An account is a config dir; the default account is the *absence* of the
    # variable, since claude keeps its config file outside ~/.claude.
    env = dict(os.environ)
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = config_dir
    else:
        env.pop("CLAUDE_CONFIG_DIR", None)

    proc = PtyProcess.spawn(argv, cwd=folder, dimensions=(40, 120), env=env)

    trust_sent = [0]
    last = [0.0]
    buf = [""]
    ready_at = [None]
    prompt_sent = [not prompt]
    logged = [0]  # mirror the first 64KB of console output to the token log

    def drain():
        while True:
            try:
                data = proc.read(2048)
            except EOFError:
                break
            except Exception:
                break
            if not data:
                time.sleep(0.1)
                continue
            if logged[0] < 65536:
                try:
                    sys.stderr.write(data)
                    sys.stderr.flush()
                except Exception:
                    pass
                logged[0] += len(data)
            buf[0] = (buf[0] + data)[-8000:]
            norm = ANSI.sub("", buf[0]).lower().replace(" ", "").replace("\n", "").replace("\r", "")
            if _wanted_option(norm) and trust_sent[0] < 6 and time.time() - last[0] > 1.5:
                try:
                    time.sleep(0.5)  # let the picker finish mounting
                    if _needs_down(norm):
                        proc.write("\x1b[B")  # move to "Yes, I trust this folder"
                        time.sleep(0.5)
                    proc.write("\r")
                except Exception:
                    pass
                trust_sent[0] += 1
                last[0] = time.time()
                # only retry if claude re-renders the prompt (a 2nd Down would wrap
                # back to "No, exit" and Enter would quit the session)
                buf[0] = ""
            if ready_at[0] is None and ("remotecontrol" in norm or "claude.ai/code" in norm):
                ready_at[0] = time.time()

    t = threading.Thread(target=drain, daemon=True)
    t.start()

    # inject the prompt once the session is ready (interactive, no claude -p)
    start = time.time()
    while not prompt_sent[0]:
        # fallback: assume ready ~8s after start if no READY marker was seen
        if ready_at[0] is None and time.time() - start > 8:
            ready_at[0] = time.time()
        if ready_at[0] and time.time() - ready_at[0] > 4:
            try:
                # bracketed paste so the seed's newlines don't submit line-by-line
                proc.write("\x1b[200~" + prompt + "\x1b[201~")
                time.sleep(0.5)
                proc.write("\r")
            except Exception:
                pass
            prompt_sent[0] = True
        elif not proc.isalive():
            break
        else:
            time.sleep(0.5)

    # keep the ConPTY open for the lifetime of the session
    while proc.isalive():
        time.sleep(1.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
