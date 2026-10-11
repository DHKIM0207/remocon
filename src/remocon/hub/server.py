"""Hub — registry + UI host + authenticated proxy to agents.

The browser talks only to this server (no secret in the browser). It serves the
static UI, exposes the machine registry, and proxies /api/m/<machine_id>/<path>
to that machine's agent, attaching that machine's bearer secret. It also owns
the SSH tunnels to remote agents (see tunnels.py), so registering or removing a
machine takes effect without restarting anything.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .. import __version__, paths
from ..config import load_config, os_name, save_config
from ..host.proc import detached_kwargs
from ..host.terminal import open_terminal
from . import enroll
from .tunnels import TunnelManager

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml",
                ".png": "image/png", ".ico": "image/x-icon", ".json": "application/json"}


def _spawn_deploy(args: list, log: Path) -> None:
    """Run `remocon deploy` in the background; it outlives this request."""
    env = dict(__import__("os").environ, PYTHONPATH=str(paths.package_root()))
    subprocess.Popen([sys.executable, "-m", "remocon", "deploy", *args],
                     stdin=subprocess.DEVNULL, stdout=open(log, "wb"), stderr=subprocess.STDOUT,
                     close_fds=True, env=env, **detached_kwargs())

def build_registry(cfg: dict) -> list[dict]:
    """Registry from config: the local machine (control host) + each entry in
    config['machines'] (registered by host + SSH user, reached via a local SSH
    tunnel on its localPort). No dependency on Tailscale — host can be any IP or
    hostname the control machine can SSH to."""
    agent_port = cfg["agent"]["port"]
    self_name = cfg.get("selfName") or socket.gethostname().split(".")[0]
    import getpass
    ctl_host = (cfg.get("control") or {}).get("host") or ""
    self_ssh_host = ctl_host if ctl_host and ctl_host not in ("127.0.0.1", "0.0.0.0", "localhost") else ""
    machines = [{
        "id": cfg.get("selfId", "local"), "name": self_name, "os": os_name(),
        "host": "localhost", "online": True, "is_self": True, "agentReady": True,
        "sshUser": cfg.get("selfSshUser") or getpass.getuser(),
        "sshHost": self_ssh_host, "sshPort": 22,
        "baseUrl": f"http://127.0.0.1:{agent_port}",
    }]
    for m in cfg.get("machines", []):
        if not m.get("id") or not m.get("localPort"):
            continue
        machines.append({
            "id": m["id"], "name": m.get("name", m["id"]), "os": m.get("os", "linux"),
            "host": m.get("host"), "online": True, "is_self": False, "agentReady": True,
            "sshUser": m.get("sshUser") or "", "sshPort": int(m.get("sshPort") or 22),
            "baseUrl": f"http://127.0.0.1:{m['localPort']}",
        })
    return machines


def _make_handler(cfg: dict, tunnels: TunnelManager | None = None):
    registry = {"by_id": {}, "cfg": cfg}

    def refresh():
        c = load_config()  # re-read so newly deployed agents appear w/o a restart
        registry["cfg"] = c
        if tunnels:
            tunnels.reconcile(c)
        machines = build_registry(c)
        registry["by_id"] = {m["id"]: m for m in machines}
        return machines

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            try:
                if sys.stderr:
                    sys.stderr.write("control %s - %s\n" % (self.address_string(), fmt % args))
            except Exception:
                pass

        # ---- static + api routing --------------------------------------
        def do_GET(self):
            u = urlparse(self.path)
            if u.path in ("/", "/index.html"):
                return self._serve_static("index.html")
            if u.path.startswith("/assets/"):
                return self._serve_static(u.path.lstrip("/"))
            if u.path == "/favicon.ico":   # browsers ask for this regardless of <link rel=icon>
                return self._serve_static("assets/favicon.svg")
            if u.path == "/api/status":
                return self._json({"version": __version__, "os": os_name(),
                                   "tunnels": tunnels.states() if tunnels else {}})
            if u.path == "/api/machines":
                return self._json({"machines": refresh()})
            if u.path == "/enroll":
                return self._enroll()
            if u.path == "/api/manager":
                return self._manager()
            if u.path == "/api/prefs":
                return self._json({"ui": load_config().get("ui") or {}})
            if u.path.startswith("/api/m/"):
                return self._proxy("GET")
            return self._json({"error": "not found"}, 404)

        def do_POST(self):
            p = urlparse(self.path).path
            if p == "/api/prefs":
                b = self._read_body() or {}
                cfg = load_config()
                ui = cfg.setdefault("ui", {})
                if b.get("lang") in ("ko", "en"):
                    ui["lang"] = b["lang"]
                if "defaultModel" in b:
                    ui["defaultModel"] = str(b["defaultModel"] or "")[:40]
                if "showCodex" in b:
                    ui["showCodex"] = bool(b["showCodex"])
                if "defaultEffort" in b:
                    v = str(b["defaultEffort"] or "")
                    if v in ("", "low", "medium", "high", "xhigh", "max"):
                        ui["defaultEffort"] = v
                self._save_cfg(cfg)
                return self._json({"ok": True, "ui": ui})
            if p == "/api/terminal":
                return self._terminal()
            if p == "/api/deploy":
                return self._deploy()
            if p == "/api/machines/add":
                return self._m_add()
            if p == "/api/machines/rename":
                return self._m_rename()
            if p == "/api/machines/remove":
                return self._m_remove()
            if p.startswith("/api/m/"):
                return self._proxy("POST")
            return self._json({"error": "not found"}, 404)

        def _read_body(self):
            n = int(self.headers.get("Content-Length", 0) or 0)
            try:
                return json.loads(self.rfile.read(n) or b"{}") if n else {}
            except json.JSONDecodeError:
                return None

        def _save_cfg(self, cfg):
            save_config(cfg)
            registry["cfg"] = cfg
            if tunnels:
                tunnels.reconcile(cfg)

        def _ssh_cmd(self, target, run, cwd):
            """Build an ssh -t command from the client machine to `target`."""
            cfgm = next((x for x in registry["cfg"].get("machines", []) if x.get("id") == target["id"]), {})
            user, host = cfgm.get("sshUser") or "", target.get("host") or ""
            port = int(cfgm.get("sshPort") or 22)
            pflag = f" -p {port}" if port != 22 else ""
            if not user or not host:
                return None
            bq = "\\\""
            if target.get("os") == "windows":
                return f'ssh -t{pflag} {user}@{host} "cd /d {bq}{cwd}{bq} && {run}"'
            return f"ssh -tt{pflag} {user}@{host} 'bash -lc \"cd {bq}{cwd}{bq} && exec {run}\"'"

        def _client_machine(self, machines):
            """Which registered machine is the browser on? Match the HTTP client
            IP against each machine's tailnet host; fall back to the control mac."""
            ip = self.client_address[0]
            for m in machines:
                if not m.get("is_self") and m.get("host") == ip:
                    return m
            return next((m for m in machines if m.get("is_self")), None)

        def _terminal(self):
            """Open a codex terminal on the PC the browser is actually on.

            The control host identifies the client machine by its tailnet IP. If
            that's the mac, it opens Terminal.app here; if it's a remote PC, it
            asks that PC's agent to open a window on its own desktop. The codex
            command runs locally when the session lives on the client machine,
            otherwise via ssh -t to the target."""
            b = self._read_body() or {}
            mid = b.get("mid") or ""
            cwd = (b.get("cwd") or "").strip()
            sid = (b.get("sessionId") or "").strip()
            model = (b.get("model") or "").strip()
            machines = refresh()
            target = registry["by_id"].get(mid)
            if not target or not cwd:
                return self._json({"error": "mid/cwd required"}, 400)
            run = f"codex resume {sid}" if sid else "codex"
            if model:
                run += f" -m {model}"

            client = self._client_machine(machines)
            on_client = client and client["id"] == target["id"]
            if on_client:
                cmd = f'cd "{cwd}" && {run}'      # session lives on the client PC
            else:
                cmd = self._ssh_cmd(target, run, cwd)   # client ssh's into the target
                if not cmd:
                    return self._json({"error": "target machine has no ssh info"}, 400)

            # Open the window on the client PC: the hub machine opens it
            # directly, a remote client PC opens it via its own agent.
            if client and client.get("is_self"):
                r = open_terminal(cmd)
                r.setdefault("where", client["name"])
                r.setdefault("cmd", cmd)
                return self._json(r)

            # remote client PC → ask its agent to open a window
            secret = registry["cfg"]["secret"]
            for mm in registry["cfg"].get("machines", []):
                if mm.get("id") == client["id"] and mm.get("secret"):
                    secret = mm["secret"]
                    break
            try:
                req = urllib.request.Request(
                    client["baseUrl"].rstrip("/") + "/termopen",
                    data=json.dumps({"cmd": cmd}).encode(), method="POST")
                req.add_header("Authorization", f"Bearer {secret}")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    r = json.loads(resp.read() or b"{}")
                r.setdefault("where", client["name"])
                r.setdefault("cmd", cmd)
                return self._json(r)
            except Exception as e:
                return self._json({"ok": False, "error": str(e), "cmd": cmd})

        def _m_add(self):
            import re as _re
            import secrets as _secrets
            b = self._read_body() or {}
            host, user = (b.get("host") or "").strip(), (b.get("sshUser") or "").strip()
            name = (b.get("name") or host).strip()
            if not host or not user:
                return self._json({"error": "host + sshUser required"}, 400)
            cfg = load_config()
            machines = cfg.setdefault("machines", [])
            base = _re.sub(r"[^a-z0-9-]+", "-", (b.get("id") or name or host).lower()).strip("-") or "machine"
            mid, i = base, 2
            taken = {m["id"] for m in machines} | {cfg.get("selfId", "local")}
            while mid in taken:
                mid, i = f"{base}-{i}", i + 1
            used = {m.get("localPort") for m in machines}
            port = next(p for p in range(9101, 9200) if p not in used)
            machines.append({"id": mid, "name": name, "host": host, "sshUser": user,
                             "sshPort": int(b.get("sshPort") or 22), "os": b.get("os", "windows"),
                             "agentPort": 8766, "localPort": port, "secret": _secrets.token_hex(32)})
            self._save_cfg(cfg)
            log = paths.logs_dir() / f"deploy-{mid}.log"
            _spawn_deploy([mid, host, user, "--ssh-port", str(int(b.get("sshPort") or 22))], log)
            refresh()
            return self._json({"ok": True, "id": mid, "deploying": True, "log": str(log)})

        def _m_rename(self):
            b = self._read_body() or {}
            mid, name = b.get("id"), (b.get("name") or "").strip()
            if not mid or not name:
                return self._json({"error": "id + name required"}, 400)
            cfg = load_config()
            if mid == cfg.get("selfId", "local"):
                cfg["selfName"] = name
            else:
                for m in cfg.get("machines", []):
                    if m.get("id") == mid:
                        m["name"] = name
                        break
                else:
                    return self._json({"error": "unknown machine"}, 404)
            self._save_cfg(cfg)
            refresh()
            return self._json({"ok": True})

        def _m_remove(self):
            b = self._read_body() or {}
            mid = b.get("id")
            cfg = load_config()
            cfg["machines"] = [m for m in cfg.get("machines", []) if m.get("id") != mid]
            self._save_cfg(cfg)   # also drops that machine's tunnel
            refresh()
            return self._json({"ok": True})

        def _manager(self):
            # open/continue (or, with ?fresh=1, reset) the persistent orchestration
            # manager on the control host
            cfg = load_config()
            from urllib.parse import parse_qs
            qs = parse_qs(urlparse(self.path).query)
            fresh = qs.get("fresh", ["0"])[0] in ("1", "true")
            delete = qs.get("delete", ["0"])[0] in ("1", "true")
            mdir = str(paths.manager_dir())
            target = f"http://127.0.0.1:{cfg['agent']['port']}/manager"
            body = json.dumps({"cwd": mdir, "fresh": fresh, "delete": delete}).encode()
            req = urllib.request.Request(target, data=body, method="POST")
            req.add_header("Authorization", f"Bearer {cfg['secret']}")
            req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data, status = resp.read(), resp.status
            except urllib.error.URLError as e:
                return self._json({"error": f"manager agent unreachable: {e.reason}"}, 502)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _enroll(self):
            from urllib.parse import parse_qs
            target_os = parse_qs(urlparse(self.path).query).get("os", ["windows"])[0]
            script = enroll.script_for(target_os)
            if script is None:
                return self._json({"error": "no SSH public key on the hub — run: ssh-keygen -t ed25519"}, 500)
            data = script.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _deploy(self):
            n = int(self.headers.get("Content-Length", 0) or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return self._json({"error": "bad json"}, 400)
            name = body.get("name")
            refresh()
            entry = next((mm for mm in registry["cfg"].get("machines", []) if mm.get("id") == name), None)
            if not entry or not entry.get("host") or not entry.get("sshUser"):
                return self._json({"error": f"machine '{name}' needs host+sshUser in config"}, 400)
            log = paths.logs_dir() / f"deploy-{name}.log"
            args = [name, entry["host"], entry["sshUser"], "--ssh-port", str(int(entry.get("sshPort") or 22))]
            if entry.get("pythonExe"):
                args += ["--python", entry["pythonExe"]]
            _spawn_deploy(args, log)
            return self._json({"ok": True, "started": name, "log": str(log)})

        def do_DELETE(self):
            if urlparse(self.path).path.startswith("/api/m/"):
                return self._proxy("DELETE")
            return self._json({"error": "not found"}, 404)

        # ---- proxy -----------------------------------------------------
        def _proxy(self, method):
            # /api/m/<machine_id>/<rest...>?<query>
            u = urlparse(self.path)
            parts = u.path[len("/api/m/"):].split("/", 1)
            mid = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            m = registry["by_id"].get(mid)
            if m is None:
                refresh()
                m = registry["by_id"].get(mid)
            if not m:
                return self._json({"error": f"unknown machine {mid}"}, 404)
            if not m.get("agentReady") or not m.get("baseUrl"):
                return self._json(
                    {"error": f"agent not deployed on '{m['name']}' yet"}, 503
                )
            # per-machine secret from config['machines']; self/local uses cfg['secret']
            agent_secret = registry["cfg"]["secret"]
            for mm in registry["cfg"].get("machines", []):
                if mm.get("id") == mid and mm.get("secret"):
                    agent_secret = mm["secret"]
                    break
            target = m["baseUrl"].rstrip("/") + "/" + rest
            if u.query:
                target += "?" + u.query
            body = None
            n = int(self.headers.get("Content-Length", 0) or 0)
            if n:
                body = self.rfile.read(n)
            req = urllib.request.Request(target, data=body, method=method)
            req.add_header("Authorization", f"Bearer {agent_secret}")
            if body is not None:
                req.add_header("Content-Type", "application/json")
            try:
                tmo = 300 if rest.split("?", 1)[0] in ("run", "handoff") else 60
                with urllib.request.urlopen(req, timeout=tmo) as resp:
                    data = resp.read()
                    status = resp.status
            except urllib.error.HTTPError as e:
                data = e.read()
                status = e.code
            except urllib.error.URLError as e:
                return self._json({"error": f"agent unreachable: {e.reason}"}, 502)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        # ---- helpers ---------------------------------------------------
        def _json(self, obj, status=200):
            data = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _serve_static(self, name):
            f = (WEB_DIR / name).resolve()
            if WEB_DIR.resolve() not in f.parents or not f.is_file():
                return self._json({"error": "not found"}, 404)
            data = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", STATIC_TYPES.get(f.suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(data)

    return Handler


def serve(cfg: dict | None = None, tunnels: TunnelManager | None = None) -> ThreadingHTTPServer:
    """Bind the hub and return the server; the caller runs serve_forever()."""
    cfg = cfg or load_config()
    if tunnels is None:
        tunnels = TunnelManager()
    tunnels.reconcile(cfg)
    host = cfg["control"]["host"]
    port = int(cfg["control"]["port"])
    httpd = ThreadingHTTPServer((host, port), _make_handler(cfg, tunnels))
    n = len(build_registry(cfg))
    sys.stderr.write(f"remocon hub {__version__} on http://{host}:{port}  ({n} machine(s))\n")
    return httpd


def main():
    serve().serve_forever()


if __name__ == "__main__":
    main()
