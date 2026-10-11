#!/usr/bin/env python3
"""CLI for the Remocon hub — read-only inspection of
sessions across machines (list machines/folders/sessions, read a transcript).

  remocon_cli.py machines
  remocon_cli.py folders    <machine>
  remocon_cli.py sessions   <machine> <cwd>
  remocon_cli.py transcript <machine> <sessionId>            # READ-ONLY: what a session is doing

`transcript` never interrupts a session — it reads the local jsonl. To start or
continue a session interactively, open its claude.ai/code URL from the web UI.
"""
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_TRANSIENT = (http.client.RemoteDisconnected, http.client.BadStatusLine,
              ConnectionError, urllib.error.URLError)


def control_url():
    u = os.environ.get("REMOCON_URL")
    if u:
        return u.rstrip("/")
    try:
        home = os.environ.get("REMOCON_HOME") or os.path.expanduser("~/.remocon")
        c = json.load(open(os.path.join(home, "config.json")))
        return f"http://{c['control']['host']}:{c['control']['port']}"
    except Exception:
        return "http://127.0.0.1:8765"


def req(path, method="GET", body=None, timeout=60, retries=3):
    """HTTP with retry on transient disconnects (e.g. RemoteDisconnected)."""
    data = json.dumps(body).encode() if body is not None else None
    last = None
    for attempt in range(retries):
        try:
            r = urllib.request.Request(control_url() + path, data=data, method=method)
            if data is not None:
                r.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:          # real HTTP error -> don't retry
            try:
                return json.load(e)
            except Exception:
                return {"error": f"HTTP {e.code}"}
        except _TRANSIENT as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    return {"error": f"connection failed after {retries} tries: {last}"}


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else "machines"
    if cmd == "machines":
        for m in req("/api/machines")["machines"]:
            print(f"{m['id']:18} {m.get('name',''):16} ready={m['agentReady']!s:5} {m.get('host','')}")
    elif cmd == "folders":
        for f in req(f"/api/m/{a[1]}/folders").get("folders", []):
            live = f" [{f.get('live')} live]" if f.get("live") else ""
            print(f"{f['session_count']:4}  {f['cwd']}{live}")
    elif cmd == "sessions":
        q = urllib.parse.quote(a[2])
        for s in req(f"/api/m/{a[1]}/sessions?cwd={q}").get("sessions", []):
            print(f"{s['session_id'][:8]}  {('live ' if s.get('is_live') else '     ')}{s.get('title','')}")
    elif cmd == "transcript":
        d = req(f"/api/m/{a[1]}/transcript?sessionId={a[2]}")
        if d.get("error"):
            print("ERROR:", d["error"]); return
        print(f"# {d.get('title','')}  ({d.get('total')} msgs, showing last {len(d.get('messages',[]))})")
        for m in d.get("messages", []):
            who = "🧑" if m["role"] == "user" else "🤖"
            print(f"\n{who} {m['text']}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
