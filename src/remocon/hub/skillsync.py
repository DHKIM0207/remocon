"""Automatic skill sync across all agents.

Periodically converges every machine's ~/.claude/skills to the newest version of
each skill (per-skill last-write-wins by mtime). The user edits skills anywhere;
this propagates the latest everywhere — no manual "what's newest / push where".

Secret/credential files are never compared or transferred (see skills.py).
Run once: remocon skills-sync   |   the hub also runs it every skillSync.intervalMin minutes.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request

import threading

from ..config import load_config


def _machines(cfg: dict) -> list[dict]:
    """{id, base, secret} for the local agent + every provisioned remote agent."""
    out = [{"id": cfg.get("selfId", "local"),
            "base": f"http://127.0.0.1:{cfg['agent']['port']}", "secret": cfg["secret"]}]
    for m in cfg.get("machines", []):
        if m.get("localPort") and m.get("secret"):
            out.append({"id": m["id"], "base": f"http://127.0.0.1:{m['localPort']}", "secret": m["secret"]})
    return out


def _req(m: dict, path: str, method: str = "GET", payload=None, timeout: int = 180):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(m["base"].rstrip("/") + "/" + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + m["secret"])
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def sync(include_empty: bool = True) -> dict:
    cfg = load_config()
    machines = _machines(cfg)
    lists = {}
    for m in machines:
        try:
            lists[m["id"]] = {s["name"]: s for s in _req(m, "skills")["skills"]}
        except Exception as e:
            print(f"[skillsync] skip {m['id']}: {e}", file=sys.stderr)
    online = [m for m in machines if m["id"] in lists]
    by_id = {m["id"]: m for m in online}
    names = set().union(*[set(lists[m["id"]]) for m in online]) if online else set()

    pushes, errors = 0, 0
    for name in sorted(names):
        owners = [mid for mid in by_id if name in lists[mid]]
        winner = max(owners, key=lambda mid: lists[mid][name]["mtime"])
        whash = lists[winner][name]["hash"]
        # all online machines converge to the newest version of each skill
        targets = [mid for mid in by_id
                   if (lists[mid].get(name) or {}).get("hash") != whash]
        if not targets:
            continue
        try:
            content = _req(by_id[winner], "skills/pull?name=" + urllib.parse.quote(name))["skills"]
        except Exception as e:
            print(f"[skillsync] pull {name} from {winner} failed: {e}", file=sys.stderr)
            errors += 1
            continue
        for mid in targets:
            try:
                _req(by_id[mid], "skills/apply", "POST", {"skills": content})
                pushes += 1
            except Exception as e:
                print(f"[skillsync] apply {name} -> {mid} failed: {e}", file=sys.stderr)
                errors += 1
    summary = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "machines": [m["id"] for m in online],
        "skills": len(names),
        "pushes": pushes,
        "errors": errors,
    }
    print("[skillsync] " + json.dumps(summary, ensure_ascii=False))
    return summary


def start_loop(cfg: dict) -> threading.Thread | None:
    """Background sync every skillSync.intervalMin minutes (0 disables)."""
    minutes = float((cfg.get("skillSync") or {}).get("intervalMin", 10) or 0)
    if minutes <= 0:
        return None

    def loop():
        while True:
            time.sleep(minutes * 60)
            try:
                sync()
            except Exception as e:
                print(f"[skillsync] failed: {e}", file=sys.stderr)

    t = threading.Thread(target=loop, daemon=True, name="skillsync")
    t.start()
    return t


if __name__ == "__main__":
    sync()
