"""SSH tunnels to every registered machine, managed inside the hub process.

For each entry in config['machines'] a forward-only tunnel
(127.0.0.1:localPort -> host:agentPort) is kept alive with auto-reconnect, so
the hub reaches each remote agent at http://127.0.0.1:<localPort>. Key auth
over plain OpenSSH (built into Windows 10+, macOS and Linux); no Tailscale.

The manager lives in the hub rather than in a separate OS job, so adding or removing a machine just calls reconcile() — no OS-specific
restart of another service.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time


def _key(m: dict) -> tuple:
    return (m.get("sshUser"), m.get("host"), int(m.get("sshPort") or 22),
            int(m["localPort"]), int(m.get("agentPort") or 8766))


class _Tunnel:
    def __init__(self, m: dict):
        self.m = dict(m)
        self.stop = threading.Event()
        self.proc: subprocess.Popen | None = None
        self.state = "starting"
        threading.Thread(target=self._loop, daemon=True, name=f"tunnel-{m['id']}").start()

    def _argv(self) -> list:
        m = self.m
        target = f"{m['sshUser']}@{m['host']}" if m.get("sshUser") else m["host"]
        return ["ssh", "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes",
                "-o", "ServerAliveInterval=20", "-o", "ServerAliveCountMax=3",
                "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=accept-new",
                "-p", str(m.get("sshPort") or 22), "-N",
                "-L", f"{m['localPort']}:127.0.0.1:{m.get('agentPort') or 8766}", target]

    def _loop(self):
        delay = 3
        while not self.stop.is_set():
            started = time.time()
            try:
                self.proc = subprocess.Popen(self._argv(), stdin=subprocess.DEVNULL,
                                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                self.state = "up"
                _, err = self.proc.communicate()
                if err and not self.stop.is_set():
                    sys.stderr.write(f"[tunnels] {self.m['id']}: {err.decode(errors='replace').strip()}\n")
            except Exception as e:
                sys.stderr.write(f"[tunnels] {self.m['id']} error: {e}\n")
            self.state = "down"
            # back off while a machine stays unreachable, reset once it held up
            delay = 3 if time.time() - started > 60 else min(delay * 2, 60)
            self.stop.wait(delay)

    def close(self):
        self.stop.set()
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()


class TunnelManager:
    def __init__(self):
        self._tunnels: dict[str, tuple[tuple, _Tunnel]] = {}
        self._lock = threading.Lock()

    def reconcile(self, cfg: dict) -> None:
        """Start tunnels for new/changed machines, stop ones that were removed."""
        want = {m["id"]: m for m in cfg.get("machines", [])
                if m.get("id") and m.get("host") and m.get("localPort")}
        with self._lock:
            for mid in list(self._tunnels):
                k, t = self._tunnels[mid]
                if mid not in want or _key(want[mid]) != k:
                    t.close()
                    del self._tunnels[mid]
            for mid, m in want.items():
                if mid not in self._tunnels:
                    self._tunnels[mid] = (_key(m), _Tunnel(m))
                    sys.stderr.write(f"[tunnels] {mid} -> {m['host']}:{m.get('agentPort') or 8766}"
                                     f" on :{m['localPort']}\n")

    def states(self) -> dict:
        with self._lock:
            return {mid: t.state for mid, (_, t) in self._tunnels.items()}

    def close(self):
        with self._lock:
            for _, t in self._tunnels.values():
                t.close()
            self._tunnels.clear()
