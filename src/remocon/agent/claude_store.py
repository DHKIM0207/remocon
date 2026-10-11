"""Filesystem-level reads of Claude Code's local session store.

Everything here is verified against claude 2.1.161 on macOS:

- Sessions live at ~/.claude/projects/<ENCODED_CWD>/<session-uuid>.jsonl
- ENCODED_CWD is LOSSY (every non [A-Za-z0-9-] char -> '-'), so we NEVER reverse
  the dir name; the authoritative cwd is read from the jsonl content.
- Live sessions are described by ~/.claude/sessions/<pid>.json (pid is the
  re-exec'd grandchild, so match by cwd + recency + liveness, never by pid).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from ..paths import adopt_legacy


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


def projects_dir() -> Path:
    return claude_home() / "projects"


def sessions_dir() -> Path:
    return claude_home() / "sessions"


def skills_dir() -> Path:
    return claude_home() / "skills"


def _names_file() -> Path:
    h = claude_home()
    return adopt_legacy(h / ".remocon-session-names.json", h / ".csm-session-names.json")


def session_names() -> dict:
    """User-chosen session names {sessionId: name}, recorded by the agent at launch
    (the remote-control name isn't stored in the pidfile/jsonl)."""
    try:
        return json.loads(_names_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _accounts_file() -> Path:
    h = claude_home()
    return adopt_legacy(h / ".remocon-session-accounts.json", h / ".csm-session-accounts.json")


def session_accounts() -> dict:
    """{sessionId: account name} for sessions this manager launched. Claude has
    no idea which of our accounts it was started under, so we record it at
    launch; "" means the machine's own login."""
    try:
        return json.loads(_accounts_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def set_session_account(session_id: str, account: str) -> None:
    d = session_accounts()
    if d.get(session_id) == account:
        return
    d[session_id] = account
    try:
        _accounts_file().write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass


def set_session_name(session_id: str, name: str) -> None:
    if not session_id or not name:
        return
    d = session_names()
    d[session_id] = name
    try:
        _names_file().write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass


def _text(content) -> str:
    """Normalize a message 'content' field (str or list of blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""


def _iso(ms_or_str):
    """Best-effort millis-epoch -> iso string passthrough."""
    if isinstance(ms_or_str, (int, float)):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms_or_str / 1000))
    return ms_or_str


_parse_cache: dict = {}     # str(path) -> ((size, mtime_ns), row)


def parse_session(path: Path, find: str = "") -> dict:
    """Cached wrapper: a transcript is only re-read when it has changed.

    Every folder click lists every session in it, and one transcript here is
    539MB — a full second per click for a file that may not have changed in
    days. Size plus mtime is enough to tell; a search (`find`) always reads,
    since its snippet depends on the term."""
    if find:
        return _parse_session(path, find)
    try:
        st = path.stat()
        key = (st.st_size, st.st_mtime_ns)
    except OSError:
        return _parse_session(path, find)
    hit = _parse_cache.get(str(path))
    if hit and hit[0] == key:
        return dict(hit[1])
    row = _parse_session(path, find)
    _parse_cache[str(path)] = (key, dict(row))
    return row


def _parse_session(path: Path, find: str = "") -> dict:
    """Single-pass parse of one session jsonl into a picker row.

    Returns keys: session_id, cwd, title, first_prompt, last_activity (epoch
    seconds), msg_count, git_branch, is_remote_control, bridge_session_id.

    `find` (already lowercased) also collects a `snippet` showing where the term
    occurs. It rides along on this pass on purpose: search would otherwise read
    every matched transcript twice, and these files reach 100MB.
    """
    finds = _str_needles(find) if find else ()
    session_id = path.stem
    cwd = None
    ai_title = None
    first_prompt = None
    git_branch = None
    bridge_session_id = None
    is_remote_control = False
    msg_count = 0
    last_ts = 0.0
    model = None
    snippet = None
    scanned = 0

    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if finds and snippet is None and scanned <= SNIPPET_BYTE_CAP:
                    scanned += len(line)
                    low = line.lower()
                    if any(n in low for n in finds):
                        snippet = _record_snippet(obj, find)

                t = obj.get("type")
                if cwd is None and obj.get("cwd"):
                    cwd = obj["cwd"]
                if git_branch is None and obj.get("gitBranch"):
                    git_branch = obj["gitBranch"]

                ts = obj.get("timestamp")
                if isinstance(ts, str):
                    # cheap lexical compare via parsed epoch fallback to mtime later
                    last_ts = max(last_ts, _epoch(ts))

                if t == "ai-title":
                    ai_title = obj.get("aiTitle") or ai_title
                elif t == "user":
                    msg_count += 1
                    if first_prompt is None and not obj.get("isMeta"):
                        msg = obj.get("message") or {}
                        txt = _text(msg.get("content")).strip()
                        if txt and not txt.startswith("<"):
                            first_prompt = txt[:200]
                elif t == "assistant":
                    msg_count += 1
                    _m = (obj.get("message") or {}).get("model")
                    if _m:
                        model = _m   # last one wins = current model
                elif t == "bridge-session":
                    is_remote_control = True
                    bridge_session_id = obj.get("bridgeSessionId") or bridge_session_id
                elif t == "system" and obj.get("subtype") == "bridge_status":
                    is_remote_control = True
    except OSError:
        pass

    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    last_activity = last_ts or mtime

    title = ai_title or first_prompt or "(no title)"
    return {
        "session_id": session_id,
        "cwd": cwd,
        "title": title,
        "first_prompt": first_prompt or "",
        "snippet": snippet or "",
        "last_activity": last_activity,
        "msg_count": msg_count,
        "git_branch": git_branch or "",
        "is_remote_control": is_remote_control,
        "bridge_session_id": bridge_session_id,
        "model": model or "",
    }


def session_preview(session_id: str, limit: int = 40) -> dict:
    """Readable transcript preview (last `limit` real user/assistant messages)
    so the UI can show what a session was about before resuming it."""
    f = find_session_file(session_id)
    if f is None:
        return {"error": "not found"}
    title = None
    msgs = []
    model = None
    try:
        with f.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = obj.get("type")
                if t == "ai-title":
                    title = obj.get("aiTitle") or title
                elif t in ("user", "assistant"):
                    if obj.get("isMeta"):
                        continue
                    txt = _text((obj.get("message") or {}).get("content")).strip()
                    if not txt or txt.startswith("<"):
                        continue
                    msgs.append({"role": t, "text": txt[:4000], "ts": obj.get("timestamp")})
                    if t == "assistant":
                        model = (obj.get("message") or {}).get("model") or model
    except OSError as e:
        return {"error": str(e)}
    return {
        "session_id": session_id,
        "title": title or "(no title)",
        "total": len(msgs),
        "messages": msgs[-limit:],
        "model": model or "",
    }


def _epoch(iso: str) -> float:
    """Parse an ISO-8601 timestamp to epoch seconds; 0 on failure."""
    try:
        from datetime import datetime

        s = iso.replace("Z", "+00:00")
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0.0


def _first_cwd(path: Path) -> str | None:
    """Read just enough lines to learn the session's launch cwd (fast)."""
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i > 50:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("cwd"):
                    return obj["cwd"]
    except OSError:
        pass
    return None


def list_folders() -> list[dict]:
    """Group every session by its real launch cwd.

    Returns [{cwd, session_count, last_activity}] sorted by recency.
    Dirs whose sessions have no recorded cwd are grouped under their dir name.
    Live-but-unwritten sessions (just opened, no jsonl yet) are folded in so a
    freshly launched folder shows up immediately.
    """
    groups: dict[str, dict] = {}
    seen_ids: dict[str, set] = {}
    pdir = projects_dir()
    if pdir.is_dir():
        for d in pdir.iterdir():
            if not d.is_dir():
                continue
            for f in d.glob("*.jsonl"):
                cwd = _first_cwd(f) or f"(unknown:{d.name})"
                try:
                    mtime = f.stat().st_mtime
                except OSError:
                    mtime = 0.0
                g = groups.setdefault(cwd, {"cwd": cwd, "session_count": 0, "last_activity": 0.0, "live": 0})
                g["session_count"] += 1
                g["last_activity"] = max(g["last_activity"], mtime)
                seen_ids.setdefault(cwd, set()).add(f.stem)
    for s in live_sessions():
        if not s.get("cwd"):
            continue
        cwd = s["cwd"]
        g = groups.setdefault(cwd, {"cwd": cwd, "session_count": 0, "last_activity": 0.0, "live": 0})
        g["live"] += 1
        if s.get("session_id") not in seen_ids.get(cwd, ()):  # not yet counted via jsonl
            g["session_count"] += 1
        g["last_activity"] = max(g["last_activity"], (s.get("updated_at") or 0) / 1000.0)
    return sorted(groups.values(), key=lambda g: g["last_activity"], reverse=True)


def list_sessions_for_cwd(cwd: str) -> list[dict]:
    """All sessions whose launch cwd == the given path (real path match)."""
    target = _realpath(cwd)
    # "(unknown:<dir>)" pseudo-folder groups cwd-less stub sessions by their
    # physical project dir so they remain listable/deletable.
    unknown_dir = cwd[len("(unknown:"):-1] if cwd.startswith("(unknown:") and cwd.endswith(")") else None
    live = {s["session_id"]: s for s in live_sessions() if s.get("session_id")}
    names = session_names()  # user-chosen names {sessionId: name}
    accts = session_accounts()
    rows = []
    seen = set()
    pdir = projects_dir()
    if pdir.is_dir():
        for d in pdir.iterdir():
            if not d.is_dir():
                continue
            for f in d.glob("*.jsonl"):
                fc = _first_cwd(f)
                if unknown_dir is not None:
                    if not (fc is None and d.name == unknown_dir):
                        continue
                elif fc is None or _realpath(fc) != target:
                    continue
                row = parse_session(f)
                row["account"] = accts.get(row["session_id"])
                ls = live.get(row["session_id"])
                row["is_live"] = ls is not None
                if ls and ls.get("bridge_session_id"):
                    row["bridge_url"] = bridge_url(ls["bridge_session_id"])
                elif row.get("bridge_session_id"):
                    row["bridge_url"] = bridge_url(row["bridge_session_id"])
                else:
                    row["bridge_url"] = None
                if names.get(row["session_id"]):
                    row["title"] = names[row["session_id"]]
                rows.append(row)
                seen.add(row["session_id"])
    # fold in just-opened live sessions that have no jsonl yet
    for sid, s in live.items():
        if sid in seen or not s.get("cwd") or _realpath(s["cwd"]) != target:
            continue
        rows.append(
            {
                "session_id": sid,
                "cwd": s["cwd"],
                "title": names.get(sid) or "(활성 세션)",
                "first_prompt": "",
                "last_activity": (s.get("updated_at") or 0) / 1000.0,
                "msg_count": 0,
                "git_branch": "",
                "is_remote_control": bool(s.get("bridge_session_id")),
                "bridge_session_id": s.get("bridge_session_id"),
                "is_live": True,
                "bridge_url": bridge_url(s["bridge_session_id"]) if s.get("bridge_session_id") else None,
            }
        )
    rows.sort(key=lambda r: r["last_activity"], reverse=True)
    return rows


DRIVES = "::drives::"  # virtual picker root listing Windows drive letters


def browse_dir(path: str | None = None) -> dict:
    """List subdirectories of `path` (default: home) so the UI can navigate the
    machine's filesystem and pick a folder. Hidden dirs are omitted. Entries are
    flagged with has_sessions when that folder already holds Claude sessions.

    On Windows, going UP from a drive root (C:\\) lands on a virtual drive list
    (D:\\, E:\\, ...) so other drives are reachable from the picker."""
    home = str(Path.home())
    if path == DRIVES and os.name == "nt":
        import string
        entries = [{"name": f"{d}:\\", "path": f"{d}:\\", "has_sessions": False}
                   for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        return {"path": "My PC (drives)", "parent": None, "home": home,
                "has_sessions": False, "entries": entries, "files": [], "file_count": 0,
                "drives": [], "error": None}
    base = _realpath(path) if path else home
    if not os.path.isdir(base):
        base = home
    session_cwds = {f["cwd"] for f in list_folders()}
    entries = []
    files = []
    err = None
    try:
        with os.scandir(base) as it:
            for e in it:
                if e.name.startswith("."):
                    continue
                try:
                    is_dir = e.is_dir(follow_symlinks=False)
                except OSError:
                    continue
                if is_dir:
                    full = os.path.join(base, e.name)
                    entries.append({"name": e.name, "path": full, "has_sessions": full in session_cwds})
                else:
                    try:
                        size = e.stat(follow_symlinks=False).st_size
                    except OSError:
                        size = None
                    files.append({"name": e.name, "size": size})
    except OSError as ex:
        err = str(ex)
    entries.sort(key=lambda d: d["name"].lower())
    files.sort(key=lambda f: f["name"].lower())
    drives = []
    if os.name == "nt":
        import string
        drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        # at a drive root (C:\) the parent is the virtual drive list
        parent = DRIVES if os.path.splitdrive(base)[1] in ("\\", "/", "") else os.path.dirname(base)
    else:
        parent = os.path.dirname(base) if base != "/" else None
    return {
        "path": base,
        "parent": parent,
        "home": home,
        "has_sessions": base in session_cwds,
        "entries": entries,
        "files": files[:300],       # current folder's files, so the user can confirm
        "file_count": len(files),
        "drives": drives,           # Windows drive letters for the picker's side list
        "error": err,
    }


def make_dir(parent: str | None, name: str) -> dict:
    """Create a new subfolder `name` under `parent` (default: home) and return a
    fresh browse_dir() of the newly-created folder so the picker lands inside it.

    `name` may contain nested segments (a/b/c) but is constrained to stay under
    `parent` — absolute paths and `..` escapes are rejected."""
    base = _realpath(parent) if parent else str(Path.home())
    if not os.path.isdir(base):
        return {"error": "상위 폴더가 존재하지 않습니다", "parent": parent}
    name = (name or "").strip().strip("/\\")
    if not name:
        return {"error": "폴더 이름을 입력하세요"}
    if os.path.isabs(name) or (os.name == "nt" and os.path.splitdrive(name)[0]):
        return {"error": "폴더 이름에 절대경로는 쓸 수 없습니다"}
    target = os.path.normpath(os.path.join(base, name))
    # confine to base: target must be base or a descendant of it
    if target != base and not target.startswith(base + os.sep):
        return {"error": "상위 폴더 밖으로 나갈 수 없습니다"}
    if os.path.exists(target):
        if os.path.isdir(target):
            return browse_dir(target)   # already there — just navigate into it
        return {"error": "같은 이름의 파일이 이미 있습니다"}
    try:
        os.makedirs(target, exist_ok=True)
    except OSError as ex:
        return {"error": f"폴더 생성 실패: {ex}"}
    return browse_dir(target)


def search_sessions(cwd: str, query: str) -> list[dict]:
    """Search sessions within a folder by title, first prompt, AND conversation
    content. Returns matching rows (same shape as list_sessions_for_cwd) plus a
    `snippet` showing the matched text."""
    rows = list_sessions_for_cwd(cwd)
    q = (query or "").strip().lower()
    if not q:
        return rows
    out = []
    for r in rows:
        snip = _match_snippet(r, q)
        if snip is not None:
            r = dict(r)
            r["snippet"] = snip
            out.append(r)
    return out


def search_all_sessions(query: str, limit: int = 60,
                        budget_s: float = 12.0) -> dict:
    """Search every Claude session on this machine, not just one folder.

    The whole conversation lives in the session's jsonl — title, first prompt and
    every message — so one raw byte scan per file decides whether it can possibly
    match. Only files that hit get the expensive JSON parse. Files are visited
    newest-first, so a truncated run still returns the most recent matches.

    Returns {sessions, truncated, scanned, matched}. `truncated` means the result
    cap or the time budget stopped the walk, not that nothing else matches.
    """
    q = (query or "").strip()
    if not q:
        return {"sessions": [], "truncated": False, "scanned": 0, "matched": 0}
    needles = _needles(q)
    lowq = q.lower()

    files = []
    pdir = projects_dir()
    if pdir.is_dir():
        for d in pdir.iterdir():
            if not d.is_dir():
                continue
            for f in d.glob("*.jsonl"):
                try:
                    files.append((f.stat().st_mtime, f))
                except OSError:
                    continue
    files.sort(key=lambda t: t[0], reverse=True)   # newest first

    live = {s["session_id"]: s for s in live_sessions() if s.get("session_id")}
    names = session_names()
    # A session renamed in the UI carries that name only here, never in the
    # transcript, so the byte scan below can't see the very title the user is
    # reading off the screen. Match it separately.
    named = {sid: nm for sid, nm in names.items() if _norm(q) in _norm(nm)}
    deadline = time.monotonic() + budget_s
    out, scanned, truncated = [], 0, False

    for _mtime, f in files:
        if len(out) >= limit or time.monotonic() > deadline:
            truncated = True
            break
        scanned += 1
        by_name = f.stem in named
        if not by_name and not _file_has(f, needles):
            continue
        row = parse_session(f, find=lowq)
        row["account"] = session_accounts().get(row["session_id"])
        ls = live.get(row["session_id"])
        row["is_live"] = ls is not None
        if ls and ls.get("bridge_session_id"):
            row["bridge_url"] = bridge_url(ls["bridge_session_id"])
        elif row.get("bridge_session_id"):
            row["bridge_url"] = bridge_url(row["bridge_session_id"])
        else:
            row["bridge_url"] = None
        if names.get(row["session_id"]):
            row["title"] = names[row["session_id"]]
        row["agent"] = "claude"
        if not row["snippet"]:   # matched in a name or title, not in the body
            for field in (named.get(f.stem), row.get("title"), row.get("first_prompt")):
                if field and _find_loose(field, lowq)[0] >= 0:
                    row["snippet"] = _snip(field, lowq)
                    break
        out.append(row)

    out.sort(key=lambda r: r.get("last_activity") or 0, reverse=True)
    return {"sessions": out, "truncated": truncated,
            "scanned": scanned, "matched": len(out)}


def _norm(s: str) -> str:
    """Lowercased and space-free. Korean is written with the spaces the writer
    felt like using, so "과제찾기" has to find "과제 찾기"."""
    return (s or "").lower().replace(" ", "")


def _escape_form(s: str) -> str:
    r"""How a string looks inside a jsonl when the writer escaped it: non-ASCII
    as \uXXXX, everything else literal. json.dumps never escapes a space, so
    escaping one would make a multi-word term unfindable."""
    return "".join(("\\u%04x" % ord(c)) if ord(c) > 127 else c for c in s)


def _needles(q: str) -> list[bytes]:
    r"""Byte patterns to look for. A jsonl mixes raw UTF-8 with \uXXXX escapes
    (both appear in the same file), so a non-ASCII term needs both forms."""
    lowq = q.lower()
    out = [lowq.encode("utf-8")]
    if any(ord(c) > 127 for c in q):
        out.append(_escape_form(lowq).encode("utf-8"))
    return out


def _file_has(path: Path, needles: list[bytes], chunk: int = 1 << 20) -> bool:
    """Case-insensitive byte scan. bytes.lower() only folds ASCII, which is
    exactly right: Hangul and other scripts here have no case to fold."""
    longest = max(len(n) for n in needles)
    # Squeezing spaces out of every chunk costs a copy of the whole file, so do
    # it only where it pays: Korean and the like, written with whatever spacing
    # the writer chose. An ASCII term is looked for as typed.
    loose = any(b >= 0x80 for n in needles for b in n)
    squeezed_needles = [n.replace(b" ", b"") for n in needles] if loose else []
    try:
        with path.open("rb") as fh:
            tail = b""
            while True:
                buf = fh.read(chunk)
                if not buf:
                    return False
                window = (tail + buf).lower()
                for n in needles:
                    if n in window:
                        return True
                if squeezed_needles:
                    flat = window.replace(b" ", b"")
                    for n in squeezed_needles:
                        if n in flat:
                            return True
                tail = buf[-(longest - 1):] if longest > 1 else b""
    except OSError:
        return False


def _match_snippet(row: dict, q: str) -> str | None:
    for field in (row.get("title"), row.get("first_prompt")):
        if field and q in field.lower():
            return _snip(field, q)
    f = find_session_file(row.get("session_id", ""))
    if f is None:
        return None
    try:
        with f.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") in ("user", "assistant") and not obj.get("isMeta"):
                    txt = _text((obj.get("message") or {}).get("content"))
                    if txt and q in txt.lower():
                        return _snip(txt, q)
    except OSError:
        pass
    return None


# A matched session gets at most this many bytes read while looking for
# something to show. Transcripts here reach 100MB+, and the hit is almost always
# early; without a cap one giant file would eat the whole search budget.
SNIPPET_BYTE_CAP = 24 << 20


def _str_needles(q: str) -> tuple:
    r"""Forms of the term as they appear in a jsonl text line: the term itself,
    plus its \uXXXX escape, since a file mixes both."""
    out = [q]
    if any(ord(c) > 127 for c in q):
        out.append(_escape_form(q))
    return tuple(out + [n.replace(" ", "") for n in out if " " in n])


def _record_snippet(obj: dict, q: str) -> str | None:
    """Where the term shows up in one record. Prefers the conversation, then
    falls back to any text in it — a tool result, a path, a command — because
    the scan that picked this file looks at those too."""
    if obj.get("type") in ("user", "assistant") and not obj.get("isMeta"):
        txt = _text((obj.get("message") or {}).get("content"))
        if txt and _find_loose(txt, q)[0] >= 0:
            return _snip(txt, q)
    for txt in _walk_strings(obj):
        if _find_loose(txt, q)[0] >= 0:
            return _snip(txt, q)
    return None


def _walk_strings(obj, depth: int = 0):
    """Every string in a decoded record, longest-lived containers first. Bounded
    so one pathological record can't stall the search."""
    if depth > 8:
        return
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v, depth + 1)
    elif isinstance(obj, list):
        for v in obj[:200]:
            yield from _walk_strings(v, depth + 1)


def _find_loose(text: str, q: str) -> tuple[int, int]:
    """Where `q` sits in `text`, ignoring case and spacing. Returns (-1, 0) when
    it isn't there."""
    low = text.lower()
    i = low.find(q)
    if i >= 0:
        return i, len(q)
    qn = _norm(q)
    if not qn:
        return -1, 0
    squeezed, back = [], []          # spaces dropped, plus a map to the original
    for j, ch in enumerate(low):
        if ch != " ":
            squeezed.append(ch)
            back.append(j)
    k = "".join(squeezed).find(qn)
    if k < 0:
        return -1, 0
    start = back[k]
    end = back[k + len(qn) - 1] + 1
    return start, end - start


def _snip(text: str, q: str, width: int = 140) -> str:
    i, n = _find_loose(text, q)
    if i < 0:
        return text[:width]
    start = max(0, i - width // 3)
    end = min(len(text), i + n + width // 2)
    s = text[start:end].replace("\n", " ").strip()
    return ("…" if start > 0 else "") + s + ("…" if end < len(text) else "")


def bridge_url(bridge_session_id: str) -> str:
    """A bridge id may be prefixed session_ (pidfile) or cse_ (jsonl); the
    claude.ai URL uses the session_ form. Normalize the suffix."""
    suffix = bridge_session_id.split("_", 1)[-1]
    return f"https://claude.ai/code/session_{suffix}"


def live_sessions() -> list[dict]:
    """Currently-running sessions, derived from ~/.claude/sessions/<pid>.json.

    Only includes pidfiles whose pid is alive (stale files linger). Deduped by
    sessionId: claude re-execs into a versioned binary, so one session can leave
    several alive pidfiles — count it once (prefer the one with a bridge / newest)."""
    by_sid: dict[str, dict] = {}
    extra = []
    sdir = sessions_dir()
    if not sdir.is_dir():
        return extra
    for f in sdir.glob("*.json"):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        pid = obj.get("pid")
        if not pid or not _pid_alive(pid):
            continue
        entry = {
            "pid": pid,
            "session_id": obj.get("sessionId"),
            "cwd": obj.get("cwd"),
            "status": obj.get("status"),
            "bridge_session_id": obj.get("bridgeSessionId"),
            "started_at": obj.get("startedAt", 0),
            "updated_at": obj.get("updatedAt", 0),
        }
        sid = entry["session_id"]
        if not sid:
            extra.append(entry)
            continue
        prev = by_sid.get(sid)
        if (prev is None
                or (entry["bridge_session_id"] and not prev["bridge_session_id"])
                or (entry.get("updated_at", 0) > prev.get("updated_at", 0))):
            by_sid[sid] = entry
    return list(by_sid.values()) + extra


def is_session_live(session_id: str) -> bool:
    return any(s["session_id"] == session_id for s in live_sessions())


def stop_session(session_id: str) -> dict:
    """Terminate a running session by SIGTERM-ing its process (the pidfile pid
    is the re-exec'd claude process). The PTY supervisor then exits on its own."""
    import signal

    for s in live_sessions():
        if s["session_id"] == session_id:
            pid = s["pid"]
            try:
                os.kill(int(pid), signal.SIGTERM)
            except OSError as e:
                return {"ok": False, "reason": f"kill failed: {e}"}
            return {"ok": True, "pid": pid}
    return {"ok": False, "reason": "not live"}


def _pid_alive(pid) -> bool:
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if os.name == "nt":
        # os.kill(pid, 0) on Windows sends CTRL_C_EVENT — never use it for a
        # liveness probe. Query the process via OpenProcess instead.
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        k = ctypes.windll.kernel32
        h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            ok = k.GetExitCodeProcess(h, ctypes.byref(code))
            return bool(ok) and code.value == STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def _realpath(p: str) -> str:
    try:
        return os.path.realpath(os.path.expanduser(p))
    except Exception:
        return p


def find_session_file(session_id: str) -> Path | None:
    pdir = projects_dir()
    if not pdir.is_dir():
        return None
    matches = list(pdir.glob(f"*/{session_id}.jsonl"))
    return matches[0] if matches else None


def delete_session(session_id: str) -> dict:
    """Delete a session unless it's live. Removes the jsonl, its companion
    per-session dir (subagents/workflows), and its session-env dir.
    Leaves file-history/ (shared, content-hashed) untouched."""
    if is_session_live(session_id):
        return {"ok": False, "refused": True, "reason": "session is live"}
    f = find_session_file(session_id)
    if f is None:
        # no transcript on disk (e.g. a session opened but never used); sweep any
        # stale pidfile referencing it so it stops showing as a ghost.
        removed = _sweep_stale_pidfiles(session_id)
        if removed:
            return {"ok": True, "removed": removed}
        return {"ok": False, "refused": False, "reason": "not found"}
    removed = []
    try:
        f.unlink()
        removed.append(str(f))
    except OSError as e:
        return {"ok": False, "refused": False, "reason": f"unlink failed: {e}"}
    companion = f.with_suffix("")  # projects/<dir>/<id>/
    _rmtree(companion, removed)
    _rmtree(claude_home() / "session-env" / session_id, removed)
    return {"ok": True, "removed": removed}


def delete_folder_sessions(cwd: str) -> dict:
    """Delete ALL non-live sessions in a folder at once. Live sessions are
    skipped (stop them first). Returns a summary."""
    rows = list_sessions_for_cwd(cwd)
    deleted, skipped, errors = 0, 0, []
    for r in rows:
        if r.get("is_live"):
            skipped += 1
            continue
        res = delete_session(r["session_id"])
        if res.get("ok"):
            deleted += 1
        else:
            errors.append({"id": r["session_id"], "reason": res.get("reason")})
    return {"ok": True, "total": len(rows), "deleted": deleted, "skipped_live": skipped, "errors": errors}


def _sweep_stale_pidfiles(session_id: str) -> list:
    """Remove dead-pid ~/.claude/sessions/<pid>.json files for this session."""
    removed = []
    sdir = sessions_dir()
    if not sdir.is_dir():
        return removed
    for f in sdir.glob("*.json"):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if obj.get("sessionId") == session_id and not _pid_alive(obj.get("pid", -1)):
            try:
                f.unlink()
                removed.append(str(f))
            except OSError:
                pass
    return removed


def _rmtree(path: Path, removed: list):
    if not path.exists():
        return
    import shutil

    try:
        shutil.rmtree(path)
        removed.append(str(path))
    except OSError:
        pass
