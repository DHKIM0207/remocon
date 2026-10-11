"""Codex CLI adapter — read sessions from ~/.codex/sessions and run codex exec.

Codex stores each session as a rollout JSONL:
  ~/.codex/sessions/YYYY/MM/DD/rollout-<stamp>-<uuid>.jsonl
with `session_meta` (id, cwd, timestamp) and `response_item` (role + content
blocks) records. This module mirrors claude_store's Claude-session reads so the
agent can serve both behind one API; rows carry agent="codex".

Running/resuming uses `codex exec --json [resume <id>] <prompt>` (non-
interactive); the model backend is whatever the machine's codex is set up with
(ChatGPT login or a local provider).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

IS_WIN = os.name == "nt"

# Codex Desktop can mirror a Claude Code conversation into its own history
# ("external agent import"). Those rollouts are copies of a Claude session we
# already list, so showing them doubles every conversation in the picker. Hide
# them; set REMOCON_SHOW_IMPORTED_CODEX=1 to get them back.
SHOW_IMPORTED = "1" in (os.environ.get("REMOCON_SHOW_IMPORTED_CODEX"),
                        os.environ.get("CSM_SHOW_IMPORTED_CODEX"))
_UUID_RE = re.compile(
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\.jsonl$"
)
_IMPORT_MARKER = b"external-import-turn"
_imports_cache: dict = {"mtime": None, "ids": frozenset()}


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))


def sessions_dir() -> Path:
    return codex_home() / "sessions"


def codex_path() -> str | None:
    """Locate the codex binary (None when not installed)."""
    p = shutil.which("codex")
    if p:
        return p
    cand = Path.home() / ".local" / "bin" / ("codex.exe" if IS_WIN else "codex")
    return str(cand) if cand.exists() else None


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for b in content:
            if isinstance(b, dict):
                out.append(b.get("text") or b.get("input_text") or b.get("output_text") or "")
        return "".join(out)
    return ""


def parse_rollout(path: Path, want_msgs: bool = False) -> dict | None:
    """One rollout jsonl -> session row (mirrors common.parse_session keys)."""
    sid = cwd = None
    first_prompt = None
    model = None
    msgs: list = []
    last_ts = ""
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = o.get("type")
                p = o.get("payload") or {}
                ts = o.get("timestamp") or ""
                if ts:
                    last_ts = max(last_ts, ts)
                if t == "session_meta":
                    sid = p.get("id") or sid
                    cwd = p.get("cwd") or cwd
                elif t == "turn_context" and p.get("model"):
                    model = p["model"]
                elif t == "response_item" and p.get("role") in ("user", "assistant"):
                    role = p["role"]
                    txt = _text(p.get("content")).strip()
                    if not txt or txt.startswith("<"):
                        continue  # developer scaffolding / environment_context
                    if want_msgs:
                        msgs.append({"role": role, "text": txt[:12000], "ts": ts})
                    else:
                        msgs.append(1)
                    if role == "user" and first_prompt is None:
                        first_prompt = txt[:200]
    except OSError:
        return None
    if not sid:
        sid = path.stem.split("-", 1)[-1][-36:]
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    from .claude_store import _epoch  # ISO -> epoch (shared helper)
    row = {
        "session_id": sid,
        "agent": "codex",
        "cwd": cwd,
        "title": first_prompt or "(no title)",
        "first_prompt": first_prompt or "",
        "last_activity": _epoch(last_ts) or mtime,
        "msg_count": len(msgs),
        "model": model or "",
        "git_branch": "",
        "is_remote_control": False,
        "bridge_session_id": None,
        "is_live": False,
        "bridge_url": None,
        "rollout_path": str(path),
    }
    if want_msgs:
        row["messages"] = msgs
    return row


def imported_thread_ids() -> frozenset:
    """Session ids Codex Desktop imported from another agent.

    Codex records every import in external_agent_session_imports.json, which is
    both cheaper and more exact than reading the rollouts, so use it when it is
    there and re-read it only when it changes.
    """
    f = codex_home() / "external_agent_session_imports.json"
    try:
        mtime = f.stat().st_mtime
    except OSError:
        _imports_cache.update(mtime=None, ids=frozenset())
        return _imports_cache["ids"]
    if _imports_cache["mtime"] != mtime:
        ids = set()
        try:
            for r in (json.loads(f.read_text(encoding="utf-8")) or {}).get("records") or []:
                tid = r.get("imported_thread_id")
                if tid:
                    ids.add(tid)
        except (OSError, json.JSONDecodeError, AttributeError):
            ids = set()
        _imports_cache.update(mtime=mtime, ids=frozenset(ids))
    return _imports_cache["ids"]


def _is_imported(path: Path, known: frozenset) -> bool:
    m = _UUID_RE.search(path.name)
    if m and m.group(1) in known:
        return True
    if known:
        return False   # the manifest is authoritative once we have one
    try:      # no manifest (older Codex): the marker sits in the opening records
        with path.open("rb") as fh:
            return _IMPORT_MARKER in fh.read(65536)
    except OSError:
        return False


def _all_rollouts():
    d = sessions_dir()
    if not d.is_dir():
        return
    known = frozenset() if SHOW_IMPORTED else imported_thread_ids()
    for f in d.rglob("rollout-*.jsonl"):
        if SHOW_IMPORTED or not _is_imported(f, known):
            yield f


def list_sessions_for_cwd(cwd: str) -> list[dict]:
    cwd = os.path.realpath(os.path.expanduser(cwd))
    rows = []
    for f in _all_rollouts():
        r = parse_rollout(f)
        if r and r.get("cwd") and os.path.realpath(r["cwd"]) == cwd:
            rows.append(r)
    rows.sort(key=lambda r: r.get("last_activity") or 0, reverse=True)
    return rows


def list_folders() -> list[dict]:
    """cwd -> {cwd, session_count, last_activity} for codex sessions."""
    by_cwd: dict[str, dict] = {}
    for f in _all_rollouts():
        r = parse_rollout(f)
        if not r or not r.get("cwd"):
            continue
        g = by_cwd.setdefault(r["cwd"], {"cwd": r["cwd"], "session_count": 0, "last_activity": 0})
        g["session_count"] += 1
        g["last_activity"] = max(g["last_activity"], r.get("last_activity") or 0)
    return list(by_cwd.values())


def _config_projects() -> list[str]:
    """Folders from config.toml [projects] — codex's own record of project dirs."""
    import re
    cfg = codex_home() / "config.toml"
    out: list[str] = []
    if cfg.exists():
        try:
            txt = cfg.read_text(encoding="utf-8")
        except OSError:
            return out
        for m in re.finditer(r'^\[projects\.(?:"([^"]+)"|\'([^\']+)\'|([^\]"\']+))\]', txt, re.M):
            p = m.group(1) or m.group(2) or m.group(3)
            if p:
                out.append(p)
    return out


def list_projects() -> list[dict]:
    """Project folders as the Codex app sees them.

    The desktop app builds its project picker from the cwds returned by the
    app-server's `thread/list` (same RPC, same default source filter), so we
    query that and dedupe by cwd. config.toml [projects] entries are folded in
    as a fallback (marked has_sessions=False). Returns
    [{cwd, has_sessions}] newest-first."""
    import threading
    import time as _t
    cx = codex_path()
    seen: dict[str, dict] = {}
    if cx:
        p = subprocess.Popen([cx, "app-server"], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             text=True, encoding="utf-8", errors="replace", bufsize=1)
        out: list[str] = []
        threading.Thread(target=lambda: [out.append(l) for l in p.stdout], daemon=True).start()

        def send(o):
            p.stdin.write(json.dumps(o) + "\n")
            p.stdin.flush()

        def wait(rid, t=15):
            t0 = _t.time()
            while _t.time() - t0 < t:
                for l in list(out):
                    try:
                        o = json.loads(l)
                    except Exception:
                        continue
                    if o.get("id") == rid:
                        return o
                _t.sleep(0.1)
            return None

        try:
            send({"id": 1, "method": "initialize",
                  "params": {"clientInfo": {"name": "asm", "version": "1"}}})
            if wait(1, 15):
                send({"method": "initialized", "params": {}})
                _t.sleep(0.2)
                cursor = None
                for _ in range(10):   # paginate
                    params = {"limit": 100}
                    if cursor:
                        params["cursor"] = cursor
                    send({"id": 2, "method": "thread/list", "params": params})
                    r = wait(2, 15)
                    if not r or "result" not in r:
                        break
                    for th in r["result"].get("data") or []:
                        cwd = th.get("cwd")
                        if cwd and cwd not in seen:
                            seen[cwd] = {"cwd": cwd, "has_sessions": True}
                    cursor = r["result"].get("nextCursor")
                    if not cursor:
                        break
        except Exception:
            pass
        finally:
            try:
                p.terminate()
            except Exception:
                pass
    return list(seen.values())


def _appserver_session(cwd: str, prompt: str, model: str = "",
                       resume_id: str = "", timeout: int = 240) -> dict:
    """Create/continue a codex session through the app-server (thread/start +
    turn/start). Sessions made this way get source=vscode and show up in the
    Codex desktop app's list — unlike `codex exec` (source=exec, filtered out).
    Returns {ok, sessionId, response}."""
    import threading
    import time as _t
    cx = codex_path()
    if not cx:
        return {"ok": False, "error": "codex CLI not installed on this machine"}
    p = subprocess.Popen([cx, "app-server"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         text=True, encoding="utf-8", errors="replace", bufsize=1)
    out: list[str] = []
    threading.Thread(target=lambda: [out.append(l) for l in p.stdout], daemon=True).start()

    def send(o):
        p.stdin.write(json.dumps(o) + "\n")
        p.stdin.flush()

    def wait(rid, t):
        t0 = _t.time()
        while _t.time() - t0 < t:
            for l in list(out):
                try:
                    o = json.loads(l)
                except Exception:
                    continue
                if o.get("id") == rid:
                    return o
            _t.sleep(0.1)
        return None

    try:
        send({"id": 1, "method": "initialize",
              "params": {"clientInfo": {"name": "asm", "version": "1"}}})
        if not wait(1, 15):
            return {"ok": False, "error": "app-server initialize timeout"}
        send({"method": "initialized", "params": {}})
        if resume_id:
            send({"id": 2, "method": "thread/resume", "params": {"threadId": resume_id}})
        else:
            send({"id": 2, "method": "thread/start", "params": {"cwd": cwd}})
        r = wait(2, 20)
        if not r or "result" not in r:
            return {"ok": False, "error": "thread start/resume failed: " + json.dumps(r or {})[:160]}
        tid = r["result"]["thread"]["id"]
        tp = {"threadId": tid, "input": [{"type": "text", "text": prompt}]}
        if model:
            tp["model"] = model
        send({"id": 3, "method": "turn/start", "params": tp})
        wait(3, timeout)
        # Poll the rollout until the assistant reply lands — the turn response
        # arrives before the rollout/preview is flushed, and a session without a
        # preview is hidden from the app's thread/list. Keep the app-server alive
        # (don't terminate) until the reply is persisted.
        reply = ""
        for _ in range(10):
            _t.sleep(1.0)
            tx = transcript(tid)
            for m in reversed(tx.get("messages") or []):
                if m.get("role") == "assistant" and (m.get("text") or "").strip():
                    reply = m["text"]
                    break
            if reply:
                break
        return {"ok": True, "sessionId": tid, "response": reply or "(응답 생성 중 — 잠시 후 새로고침)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            p.terminate()
        except Exception:
            pass


def transcript(session_id: str) -> dict:
    for f in _all_rollouts():
        if session_id not in f.name:
            continue
        r = parse_rollout(f, want_msgs=True)
        if r and r["session_id"] == session_id:
            return {"session_id": session_id, "agent": "codex", "title": r["title"],
                    "total": len(r["messages"]), "messages": r["messages"]}
    # slow path (meta id may differ from filename)
    for f in _all_rollouts():
        r = parse_rollout(f, want_msgs=True)
        if r and r["session_id"] == session_id:
            return {"session_id": session_id, "agent": "codex", "title": r["title"],
                    "total": len(r["messages"]), "messages": r["messages"]}
    return {"error": "not found"}


def delete(session_id: str) -> dict:
    """Delete a codex session by removing its rollout jsonl."""
    for f in _all_rollouts():
        if session_id in f.name:
            try:
                f.unlink()
                return {"ok": True, "agent": "codex"}
            except OSError as e:
                return {"ok": False, "reason": str(e)}
    # slow path: id only inside the file's session_meta
    for f in _all_rollouts():
        r = parse_rollout(f)
        if r and r["session_id"] == session_id:
            try:
                f.unlink()
                return {"ok": True, "agent": "codex"}
            except OSError as e:
                return {"ok": False, "reason": str(e)}
    return {"ok": False, "reason": "not found"}


def run(body: dict) -> dict:
    """Start or resume a codex session via the app-server and return the reply.

    Uses the app-server (thread/start + turn/start) instead of `codex exec`, so
    the session is source=vscode and appears in the Codex desktop app's list
    (codex exec sessions are source=exec and filtered out by the app).

    body: {cwd, prompt, resumeId?, model?, timeoutSec?}
    Returns {ok, sessionId, response}.
    """
    cwd = os.path.realpath(os.path.expanduser(body.get("cwd", "") or "~"))
    prompt = (body.get("prompt") or "").strip()
    if not body.get("resumeId") and not os.path.isdir(cwd):
        return {"ok": False, "error": f"folder not found: {cwd}"}
    if not prompt:
        return {"ok": False, "error": "prompt required"}
    r = _appserver_session(
        cwd, prompt,
        model=(body.get("model") or "").strip(),
        resume_id=body.get("resumeId") or "",
        timeout=int(body.get("timeoutSec") or 240),
    )
    r.setdefault("agent", "codex")
    return r
