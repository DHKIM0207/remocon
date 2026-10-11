"""remocon agent — the per-machine workhorse.

A single-file stdlib HTTP service that owns this machine's ~/.claude: it lists
folders/sessions, launches detached `claude --remote-control` sessions via the
PTY supervisor, resolves the resulting claude.ai/code URL by polling pidfiles,
and deletes sessions. The central control plane (control.py) is the only
intended caller; auth is a shared bearer secret (constant-time compared).

Run:  remocon agent   (reads ~/.remocon/config.json)
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .. import __version__, paths
from ..config import load_config, os_name, which_claude
from ..host.proc import detached_kwargs, headless_python
from ..host.terminal import open_terminal
from . import accounts, codex, skills
from . import claude_store as common

HERE = Path(__file__).resolve().parent
IS_WIN = os.name == "nt"
# The launcher runs as a plain script (not a package import) so it keeps no
# reference to the agent once a session is up.
LAUNCHER = HERE / ("launcher_win.py" if IS_WIN else "launcher_posix.py")
# On Windows, run the launcher with pythonw (no console) + CREATE_NO_WINDOW so no
# terminal window flashes when a session is launched.
LAUNCH_EXE = headless_python()

# token -> {cwd, name, started, state, url, error}
_launches: dict[str, dict] = {}
_lock = threading.Lock()


_procs: dict = {}     # token -> launcher Popen, while this agent process lives

_LOGIN_GONE = (b"Not logged in", b"Login expired")
_auth_checked: dict = {}   # token -> launch started, once its login has been asked about


def _logged_out(token: str) -> str | None:
    """A claude with no login doesn't exit — it sits at the prompt saying so —
    so the launcher stays up and the exit test above never fires. Once a launch
    has gone a few seconds without a bridge, ask that account's login state,
    once. (`auth status` can still say yes for an expired token; that case ends
    with claude exiting, which the exit test catches.)"""
    with _lock:
        rec = _launches.get(token)
        if rec is None or token in _auth_checked or time.time() - rec["started"] < 8:
            return None
        _auth_checked[token] = True
    st = accounts.status(rec.get("account") or "")
    if st.get("loggedIn") is False:
        return "이 계정은 로그인되어 있지 않습니다 — 계정(👤)에서 로그인하세요"
    return None


def _launch_dead_end(token: str, log_path) -> str | None:
    """Why this launch can never reach claude.ai/code, or None to keep waiting.

    The decision is whether the launcher has exited: it owns claude's terminal
    and leaves when claude does, so an exited launcher with no bridge is final —
    waiting out the timeout only delays the news, and that became minutes once
    big resumes were given longer. The log is NOT used to decide: a resume
    replays recent conversation on screen first, so a transcript that merely
    mentions "Not logged in" would read as a dead launch. It only picks the
    message, from the last stretch of output, where claude's own exit text is.
    """
    with _lock:
        proc = _procs.get(token)
    if proc is None:
        return None
    if proc.poll() is None:
        return _logged_out(token)
    with _lock:
        _procs.pop(token, None)
    tail = b""
    try:
        with open(log_path, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 2048))
            tail = fh.read()
    except OSError:
        pass
    if any(n in tail for n in _LOGIN_GONE):
        return "이 머신의 클로드 로그인이 만료됐습니다 — 계정(👤)에서 다시 로그인하세요"
    return "클로드가 시작 직후 종료됐습니다 — 실행 로그를 확인하세요"


def _launch_timeout(resume_id: str) -> int:
    """How long a launch may take before we call it failed.

    claude reads the whole transcript before it connects to claude.ai/code, so a
    resume of a large one takes far longer than a fresh session: a 374MB
    transcript (11k messages) blew through the old flat 45s and kept loading
    after the UI had given up. Allow 45s plus about 1s per 4MB, capped at 5 min.
    """
    if not resume_id:
        return 45
    f = common.find_session_file(resume_id)
    try:
        mb = f.stat().st_size / 1048576 if f else 0
    except OSError:
        mb = 0
    return int(min(300, 45 + mb / 4))


class Agent:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.secret = cfg["secret"].encode()
        self.claude_path = cfg.get("claudePath") or which_claude()
        self.log_dir = Path(cfg.get("logDir") or (paths.logs_dir() / "launches"))
        self.log_dir.mkdir(parents=True, exist_ok=True)

    # ---- handlers -------------------------------------------------------
    def health(self) -> dict:
        return {
            "ok": True,
            "hostname": socket.gethostname(),
            "os": os_name(),
            "claudePath": self.claude_path,
            "claudeHome": str(common.claude_home()),
            "agentVersion": __version__,
        }

    def folders(self, with_codex: bool = True) -> dict:
        # merge Claude folders with Codex folders (same cwd -> one row)
        rows = common.list_folders()
        if not with_codex:
            return {"folders": rows, "activeAccount": accounts.active()}
        by_cwd = {f["cwd"]: f for f in rows}
        for cf in codex.list_folders():
            f = by_cwd.get(cf["cwd"])
            if f:
                f["session_count"] = f.get("session_count", 0) + cf["session_count"]
                f["codex_count"] = cf["session_count"]
                f["last_activity"] = max(f.get("last_activity") or 0, cf["last_activity"])
            else:
                cf["codex_count"] = cf["session_count"]
                rows.append(cf)
                by_cwd[cf["cwd"]] = cf
        return {"folders": rows, "activeAccount": accounts.active()}

    def sessions(self, cwd: str, with_codex: bool = True) -> dict:
        rows = common.list_sessions_for_cwd(cwd)
        for r in rows:
            r.setdefault("agent", "claude")
        if with_codex:
            rows += codex.list_sessions_for_cwd(cwd)
        rows.sort(key=lambda r: r.get("last_activity") or 0, reverse=True)
        return {"sessions": rows, "activeAccount": accounts.active()}

    def browse(self, path: str | None) -> dict:
        return common.browse_dir(path)

    def mkdir(self, body: dict) -> dict:
        return common.make_dir(body.get("parent"), body.get("name") or "")

    def upload(self, body: dict) -> dict:
        """Save a base64 image to ~/.remocon/uploads and return its path — used to
        attach images to codex runs (codex exec -i <path>)."""
        import base64
        name = os.path.basename(body.get("filename") or "image.png") or "image.png"
        try:
            data = base64.b64decode(body.get("data") or "")
        except Exception:
            data = b""
        if not data:
            return {"error": "no data"}, 400
        if len(data) > 20 * 1024 * 1024:
            return {"error": "image too large (>20MB)"}, 400
        p = paths.uploads_dir() / f"{int(time.time() * 1000)}-{name}"
        p.write_bytes(data)
        return {"ok": True, "path": str(p)}

    def open_terminal(self, body: dict) -> dict:
        """Open a terminal window on THIS machine running the given command.
        Used so the codex TUI appears on whichever PC the browser is on."""
        return open_terminal(body.get("cmd") or "")

    def handoff(self, body: dict) -> dict:
        """Branch a session into a NEW session, optionally under the other agent.

        Both Claude and Codex store plain-text jsonl, so we serialize the source
        transcript (optionally truncated at `upToIndex` for a rewind) and seed a
        fresh target session with it.

        body: {sessionId, fromAgent, toAgent?, cwd, upToIndex?}
          - toAgent == fromAgent + upToIndex  -> rewind (same model, earlier point)
          - toAgent != fromAgent              -> model switch (handoff)
        Returns the codex {ok, sessionId, response} or the claude {token} to poll.
        """
        sid = body.get("sessionId") or ""
        src = body.get("fromAgent") or "claude"
        dst = body.get("toAgent") or src
        cwd = body.get("cwd") or ""
        up = body.get("upToIndex")
        if not sid:
            return {"ok": False, "error": "sessionId required"}
        # full history, not the 40-message preview window the modal uses
        tx = codex.transcript(sid) if src == "codex" else common.session_preview(sid, limit=100000)
        if tx.get("error"):
            return {"ok": False, "error": f"source transcript: {tx['error']}"}
        msgs = tx.get("messages") or []
        up_ts = body.get("upToTs")
        if up_ts:   # cut at the chosen message by timestamp (window-shift safe)
            hits = [i for i, m in enumerate(msgs) if m.get("ts") == up_ts]
            if hits:
                msgs = msgs[:hits[-1] + 1]
            elif isinstance(up, int):   # fallback: index within the UI's 40-msg tail window
                base = max(0, len(msgs) - 40)
                msgs = msgs[:min(len(msgs), base + up + 1)]
        elif isinstance(up, int) and 0 <= up < len(msgs):
            msgs = msgs[:up + 1]          # keep through the chosen message
        if not msgs:
            return {"ok": False, "error": "nothing to carry over"}
        # keep the most recent turns within a budget so the seed stays sane
        budget, kept, used = 24000, [], 0
        for m in reversed(msgs):
            t = m.get("text") or ""
            if used + len(t) > budget and kept:
                break
            kept.append(m)
            used += len(t)
        kept.reverse()
        omitted = len(msgs) - len(kept)
        rewind = (dst == src)
        head = ("[Rewind] Resuming this conversation from an earlier point. "
                "The history below is the context up to that point — continue from here."
                if rewind else
                f"[Handoff] The conversation below was carried over from another coding "
                f"agent ({src}). Continue it as if it were your own context.")
        lines = [head]
        if omitted > 0:
            lines.append(f"(... {omitted} earlier messages omitted ...)")
        for m in kept:
            who = "User" if m["role"] == "user" else "Assistant"
            lines.append(f"{who}: {m['text']}")
        lines += ["---", "Acknowledge briefly that you have the context, then continue."]
        seed = "\n".join(lines)
        if dst == "codex":
            r = codex.run({"cwd": cwd, "prompt": seed,
                           "timeoutSec": int(body.get("timeoutSec") or 240)})
            r["toAgent"] = "codex"
            return r
        tag = "rewind" if rewind else "handoff"
        r = self.launch({"cwd": cwd, "prompt": seed, "name": f"{tag}-{sid[:8]}"})
        if isinstance(r, tuple):
            return {"ok": False, "error": r[0].get("error", "launch failed")}
        r["ok"] = True
        r["toAgent"] = "claude"
        return r   # {token} — poll /launch?token= as with a normal launch

    def transcript(self, session_id: str, agent_kind: str = "") -> dict:
        if agent_kind == "codex":
            return codex.transcript(session_id)
        d = common.session_preview(session_id)
        if d.get("error") and not agent_kind:   # fall through for unlabeled codex ids
            c = codex.transcript(session_id)
            if not c.get("error"):
                return c
        return d

    def search(self, cwd: str, q: str) -> dict:
        return {"sessions": common.search_sessions(cwd, q)}

    def search_all(self, q: str, limit: int = 60) -> dict:
        """Every Claude session on this machine, not just one folder."""
        return common.search_all_sessions(q, limit=limit)

    def skills_list(self) -> dict:
        return {"skills": skills.list_skills(common.skills_dir())}

    def skills_pull(self, name: str | None = None) -> dict:
        return {"skills": skills.read_skills(common.skills_dir(), [name] if name else None)}

    def skills_apply(self, payload: dict) -> dict:
        return skills.write_skills(common.skills_dir(), payload)

    def launch(self, body: dict) -> dict:
        cwd = os.path.realpath(os.path.expanduser(body["cwd"]))
        if not os.path.isdir(cwd):
            return {"error": f"folder not found: {cwd}"}, 400
        user_name = (body.get("name") or "").strip()
        name = user_name or f"{socket.gethostname()}-{int(time.time())}"
        resume_id = body.get("resumeId") or ""
        fork = "1" if body.get("fork") else "0"
        token = secrets.token_hex(8)
        timeout = _launch_timeout(resume_id)

        # Resuming a session that is already running must not start a second
        # claude on it: two processes appending to one transcript can corrupt
        # it, and the list (which dedupes by session id) would hide the extra
        # one. This is exactly what a retry after a slow resume used to do —
        # the first attempt was still loading a huge transcript when the UI
        # gave up. So attach to what is there instead.
        if resume_id and fork == "0":
            for s in common.live_sessions():
                if s.get("session_id") != resume_id:
                    continue
                rec = {"cwd": cwd, "account": None, "name": "", "user_name": "",
                       "resume_id": resume_id, "fork": False, "attach": True,
                       "started": time.time(), "timeout": timeout,
                       "state": "spawning", "url": None, "error": None}
                if s.get("bridge_session_id"):
                    rec.update(state="ready", url=common.bridge_url(s["bridge_session_id"]))
                with _lock:
                    _launches[token] = rec
                return {"token": token, "timeout": timeout, "attached": True}

        logf = open(self.log_dir / f"{token}.log", "wb")
        argv = [LAUNCH_EXE, str(LAUNCHER), cwd, name, resume_id, fork, self.claude_path]
        prompt = (body.get("prompt") or "").strip()   # optional seed (rewind / handoff)
        model = (body.get("model") or "").strip()     # optional claude --model override
        effort = (body.get("effort") or "").strip()   # optional claude --effort override
        if effort not in ("", "low", "medium", "high", "xhigh", "max"):
            effort = ""
        acct = (body.get("account") if body.get("account") is not None
                else accounts.active())
        rc_ok, rc_org = accounts.remote_control(acct)
        if not rc_ok:
            logf.close()
            return {"error": "%s 조직은 원격 제어를 막아 두어 이 매니저로 세션을 열 수 없습니다 "
                             "— 계정(👤)에서 다른 조직의 계정으로 바꾸세요" % (rc_org or "이 계정의")}
        cfg_dir = str(accounts.config_dir_for(acct)) if acct else ""
        # positional tail: prompt, model, effort, config dir. Trim from the
        # right so an unset middle value still lines up with the launcher's
        # argv indexes.
        tail = [prompt, model, effort, cfg_dir]
        while tail and not tail[-1]:
            tail.pop()
        argv += tail
        # detached so the session outlives the agent/SSH session
        kw = dict(stdin=subprocess.DEVNULL, stdout=logf, stderr=subprocess.STDOUT, close_fds=True,
                  **detached_kwargs())
        proc = subprocess.Popen(argv, **kw)
        with _lock:
            _procs[token] = proc
        rec = {
            "cwd": cwd,
            "account": acct,
            "name": name,
            "user_name": user_name,
            "resume_id": resume_id,
            "fork": fork == "1",
            "timeout": timeout,
            "started": time.time(),
            "state": "spawning",
            "url": None,
            "error": None,
        }
        with _lock:
            _launches[token] = rec
        try:   # persist so an agent restart doesn't orphan the UI's polling
            (self.log_dir / f"{token}.launch.json").write_text(
                json.dumps(rec), encoding="utf-8")
        except OSError:
            pass
        return {"token": token, "timeout": timeout}

    def launch_status(self, token: str) -> dict:
        with _lock:
            rec = _launches.get(token)
            rec = dict(rec) if rec else None
        if rec is None and token == os.path.basename(token):
            # agent restarted mid-poll? recover the record from disk
            f = self.log_dir / f"{token}.launch.json"
            if f.exists():
                try:
                    rec = json.loads(f.read_text(encoding="utf-8"))
                    with _lock:
                        _launches[token] = dict(rec)
                except (OSError, json.JSONDecodeError):
                    rec = None
        if rec is None:
            return {"error": "unknown token"}, 404
        if rec["state"] in ("ready", "failed"):
            return rec
        # resolve. A plain resume keeps the session id, so wait for that exact
        # session to get its bridge; a new session or a fork has no id yet, so
        # take the newest bridged session in this folder that started after us.
        target = rec["cwd"]
        best = None
        by_id = rec.get("resume_id") and not rec.get("fork")
        for s in common.live_sessions():
            if not s.get("bridge_session_id"):
                continue
            if by_id:
                if s.get("session_id") == rec["resume_id"]:
                    best = s
                    break
                continue
            if not s.get("cwd") or os.path.realpath(s["cwd"]) != target:
                continue
            started_s = (s.get("started_at") or 0) / 1000.0
            if started_s and started_s < rec["started"] - 5:
                continue  # an older pre-existing session, not ours
            if best is None or (s.get("started_at") or 0) > (best.get("started_at") or 0):
                best = s
        if best:
            url = common.bridge_url(best["bridge_session_id"])
            if rec.get("user_name"):  # remember the user's chosen name for the list
                common.set_session_name(best["session_id"], rec["user_name"])
            # claude keeps no record of which of our accounts started it
            common.set_session_account(best["session_id"], rec.get("account") or "")
            with _lock:
                if token in _launches:
                    _launches[token].update(state="ready", url=url)
            rec.update(state="ready", url=url)
        elif (dead := _launch_dead_end(token, self.log_dir / f"{token}.log")):
            with _lock:
                if token in _launches:
                    _launches[token].update(state="failed", error=dead)
            rec.update(state="failed", error=dead)
        elif time.time() - rec["started"] > rec.get("timeout", 45):
            err = "timed out waiting for session (check auth / trust prompt)"
            with _lock:
                if token in _launches:
                    _launches[token].update(state="failed", error=err)
            rec.update(state="failed", error=err)
        return rec

    def manager_open(self, cwd: str, fresh: bool = False) -> dict:
        """Open (or continue) the single persistent orchestration-manager session
        in `cwd`, returning its claude.ai/code URL. Reuses a live one, else
        resumes the most recent session there, else starts fresh. No prompt.

        If `fresh`, RESET the manager: stop any live session in `cwd` and start a
        brand-new one with blank context (no resume)."""
        cwd = os.path.realpath(os.path.expanduser(cwd))
        os.makedirs(cwd, exist_ok=True)
        if fresh:
            for s in common.live_sessions():
                if s.get("cwd") and os.path.realpath(s["cwd"]) == cwd:
                    common.stop_session(s["session_id"])
            time.sleep(1.0)  # let the old PTY release before launching fresh
        else:
            for s in common.live_sessions():
                if s.get("cwd") and os.path.realpath(s["cwd"]) == cwd and s.get("bridge_session_id"):
                    return {"ok": True, "sessionId": s["session_id"], "reused": True,
                            "bridgeUrl": common.bridge_url(s["bridge_session_id"])}
        past = [] if fresh else common.list_sessions_for_cwd(cwd)
        resume_id = past[0]["session_id"] if past else ""
        started = time.time()
        logf = open(self.log_dir / "manager.log", "wb")
        argv = [LAUNCH_EXE, str(LAUNCHER), cwd, "remocon-manager", resume_id, "0", self.claude_path]
        # detached so the session outlives the agent/SSH session
        kw = dict(stdin=subprocess.DEVNULL, stdout=logf, stderr=subprocess.STDOUT, close_fds=True,
                  **detached_kwargs())
        subprocess.Popen(argv, **kw)
        while time.time() - started < 45:
            time.sleep(1.5)
            for s in common.live_sessions():
                if not s.get("cwd") or not s.get("bridge_session_id"):
                    continue
                if os.path.realpath(s["cwd"]) != cwd:
                    continue
                st = (s.get("started_at") or 0) / 1000.0
                if resume_id or not st or st >= started - 5:
                    return {"ok": True, "sessionId": s["session_id"],
                            "bridgeUrl": common.bridge_url(s["bridge_session_id"])}
        return {"ok": False, "error": "timed out opening manager"}

    def manager_delete(self, cwd: str) -> dict:
        """Delete the manager session: stop any live session in `cwd` and remove
        its stored sessions (blank slate; the next open starts brand new)."""
        cwd = os.path.realpath(os.path.expanduser(cwd))
        for s in common.live_sessions():
            if s.get("cwd") and os.path.realpath(s["cwd"]) == cwd:
                common.stop_session(s["session_id"])
        time.sleep(0.5)  # let the PTY release before removing files
        return {"ok": True, "deleted": common.delete_folder_sessions(cwd)}

    def delete(self, session_id: str) -> dict:
        return common.delete_session(session_id)

    def stop(self, session_id: str) -> dict:
        return common.stop_session(session_id)

    def delete_folder(self, cwd: str) -> dict:
        return common.delete_folder_sessions(cwd)


def _make_handler(agent: Agent):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # quieter logs; sys.stderr is None under pythonw
            try:
                if sys.stderr:
                    sys.stderr.write("agent %s - %s\n" % (self.address_string(), fmt % args))
            except Exception:
                pass

        def _authed(self) -> bool:
            hdr = self.headers.get("Authorization", "")
            token = hdr[7:] if hdr.startswith("Bearer ") else ""
            return hmac.compare_digest(token.encode(), agent.secret)

        def _send(self, obj, status=200):
            if isinstance(obj, tuple):
                obj, status = obj
            data = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self._authed():
                return self._send({"error": "unauthorized"}, 401)
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path == "/health":
                return self._send(agent.health())
            # ?codex=0 skips Codex entirely. Listing it means reading every
            # rollout on the machine — 518 files / 3.9GB here, mostly one-shot
            # `codex exec` calls — on every folder click.
            with_codex = (q.get("codex") or ["1"])[0] != "0"
            if u.path == "/folders":
                return self._send(agent.folders(with_codex))
            if u.path == "/alive":
                sid = (q.get("sessionId") or [""])[0]
                return self._send({"alive": any(x.get("session_id") == sid
                                                for x in common.live_sessions())})
            if u.path == "/codex/projects":
                return self._send({"projects": codex.list_projects()})
            if u.path == "/sessions":
                cwd = (q.get("cwd") or [""])[0]
                if not cwd:
                    return self._send({"error": "cwd required"}, 400)
                return self._send(agent.sessions(cwd, with_codex))
            if u.path == "/launch":
                token = (q.get("token") or [""])[0]
                return self._send(agent.launch_status(token))
            if u.path == "/browse":
                return self._send(agent.browse((q.get("path") or [""])[0] or None))
            if u.path == "/transcript":
                sid = (q.get("sessionId") or [""])[0]
                if not sid:
                    return self._send({"error": "sessionId required"}, 400)
                return self._send(agent.transcript(sid, (q.get("agent") or [""])[0]))
            if u.path == "/search":
                cwd = (q.get("cwd") or [""])[0]
                if not cwd:
                    return self._send({"error": "cwd required"}, 400)
                return self._send(agent.search(cwd, (q.get("q") or [""])[0]))
            if u.path == "/search-all":
                term = (q.get("q") or [""])[0]
                if not term.strip():
                    return self._send({"error": "q required"}, 400)
                try:
                    lim = max(1, min(200, int((q.get("limit") or ["60"])[0])))
                except ValueError:
                    lim = 60
                return self._send(agent.search_all(term, lim))
            if u.path == "/accounts":
                return self._send(accounts.list_accounts())
            if u.path == "/skills":
                return self._send(agent.skills_list())
            if u.path == "/skills/pull":
                return self._send(agent.skills_pull((q.get("name") or [""])[0] or None))
            return self._send({"error": "not found"}, 404)

        def do_POST(self):
            if not self._authed():
                return self._send({"error": "unauthorized"}, 401)
            u = urlparse(self.path)
            body = self._read_json()
            if u.path == "/launch":
                if not body or not body.get("cwd"):
                    return self._send({"error": "cwd required"}, 400)
                return self._send(agent.launch(body))
            if u.path == "/run":
                b = body or {}
                if b.get("agent") == "codex":
                    return self._send(codex.run(b))
                return self._send({"error": "only agent='codex' runs are supported"}, 400)
            if u.path == "/mkdir":
                return self._send(agent.mkdir(body or {}))
            if u.path == "/upload":
                return self._send(agent.upload(body or {}))
            if u.path == "/handoff":
                return self._send(agent.handoff(body or {}))
            if u.path == "/termopen":
                return self._send(agent.open_terminal(body or {}))
            if u.path == "/manager":
                b = body or {}
                cwd = b.get("cwd") or str(paths.manager_dir())
                if b.get("delete"):
                    return self._send(agent.manager_delete(cwd))
                return self._send(agent.manager_open(cwd, fresh=bool(b.get("fresh"))))
            if u.path == "/accounts/create":
                return self._send(accounts.create((body.get("name") or "").strip()))
            if u.path == "/accounts/select":
                return self._send(accounts.set_active((body.get("name") or "").strip()))
            if u.path == "/accounts/delete":
                return self._send(accounts.delete((body.get("name") or "").strip()))
            if u.path == "/accounts/logout":
                return self._send(accounts.logout((body.get("name") or "").strip()))
            if u.path == "/accounts/login":
                return self._send(accounts.login_start(
                    (body.get("name") or "").strip(), bool(body.get("console")),
                    (body.get("org") or "").strip()))
            if u.path == "/accounts/code":
                tok = (body.get("token") or "").strip()
                code = (body.get("code") or "").strip()
                if not tok or not code:
                    return self._send({"error": "token and code required"}, 400)
                return self._send(accounts.login_code(tok, code))
            if u.path == "/stop":
                if not body or not body.get("sessionId"):
                    return self._send({"error": "sessionId required"}, 400)
                return self._send(agent.stop(body["sessionId"]))
            if u.path == "/folder/delete":
                if not body or not body.get("cwd"):
                    return self._send({"error": "cwd required"}, 400)
                return self._send(agent.delete_folder(body["cwd"]))
            if u.path == "/skills/apply":
                return self._send(agent.skills_apply((body or {}).get("skills") or {}))
            return self._send({"error": "not found"}, 404)

        def do_DELETE(self):
            if not self._authed():
                return self._send({"error": "unauthorized"}, 401)
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path == "/session":
                sid = (q.get("sessionId") or [""])[0]
                if not sid:
                    return self._send({"error": "sessionId required"}, 400)
                if (q.get("agent") or [""])[0] == "codex":
                    return self._send(codex.delete(sid))
                return self._send(agent.delete(sid))
            return self._send({"error": "not found"}, 404)

        def _read_json(self):
            try:
                n = int(self.headers.get("Content-Length", 0))
            except ValueError:
                return None
            if not n:
                return {}
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return None

    return Handler


def serve(cfg: dict | None = None) -> ThreadingHTTPServer:
    """Bind the agent and return the server; the caller runs serve_forever()."""
    cfg = cfg or load_config()
    agent = Agent(cfg)
    host = cfg["agent"]["host"]
    port = int(cfg["agent"]["port"])
    # Keep default allow_reuse_address=True so the agent can rebind after a
    # restart (Windows would otherwise block on a TIME_WAIT socket). Duplicate
    # instances are prevented by running a single service, not here.
    httpd = ThreadingHTTPServer((host, port), _make_handler(agent))
    sys.stderr.write(f"remocon agent {__version__} on http://{host}:{port} (claude={agent.claude_path})\n")
    return httpd


def main():
    serve().serve_forever()


if __name__ == "__main__":
    main()
