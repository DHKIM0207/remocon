"""Windows service wrapper for the agent (pywin32).

Runs `python -m remocon agent` as a child and restarts it whenever it exits, so the
agent is up from boot with nobody logged on. The service should log on as the
user who owns the claude login (not LocalSystem), so the agent sees that user's
~/.claude and files. Services start with only the system environment, so the
user's own variables (HKCU\\Environment, e.g. PATH with ~/.local/bin) are merged
into the child's environment here.

  python remocon\\host\\winservice.py --startup auto install | update | start | stop | remove

`remocon service install agent --winservice` does this for you and falls back
to the logon task until the service is given the user's password.

Runs as a plain script under pythonservice.exe, so it must not import the
remocon package itself.
"""
import os
import subprocess
import sys
import time
import winreg

import servicemanager
import win32event
import win32service
import win32serviceutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # the dir that holds the remocon package
HOME = os.environ.get("REMOCON_HOME") or os.path.join(os.path.expanduser("~"), ".remocon")


def _user_env() -> dict:
    env = dict(os.environ)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            i = 0
            while True:
                try:
                    name, value, kind = winreg.EnumValue(k, i)
                except OSError:
                    break
                i += 1
                if kind == winreg.REG_EXPAND_SZ:
                    value = winreg.ExpandEnvironmentStrings(value)
                if name.upper() == "PATH":
                    env["PATH"] = env.get("PATH", "") + os.pathsep + value
                else:
                    env[name] = value
    except OSError:
        pass
    env.setdefault("USERPROFILE", os.path.dirname(HOME))
    env["PYTHONPATH"] = ROOT + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def _python() -> str:
    # Under the service host, sys.executable is pythonservice.exe; use the
    # interpreter that owns this pywin32 install instead.
    exe = os.path.join(sys.prefix, "python.exe")
    return exe if os.path.exists(exe) else sys.executable


class RemoconAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "Remocon-Agent"
    _svc_display_name_ = "Remocon Agent"
    _svc_description_ = "Runs the Remocon agent on 127.0.0.1:8766 and restarts it if it exits."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.child = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self._kill_child()

    def _kill_child(self):
        if self.child and self.child.poll() is None:
            # /T: also end the claude processes the agent started.
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.child.pid)], capture_output=True)

    def SvcDoRun(self):
        servicemanager.LogInfoMsg(f"{self._svc_name_} starting (root={ROOT})")
        logs = os.path.join(HOME, "logs")
        os.makedirs(logs, exist_ok=True)
        log = open(os.path.join(logs, "agent-service.log"), "a", buffering=1, encoding="utf-8")
        backoff = 2
        while True:
            started = time.time()
            log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} starting agent\n")
            self.child = subprocess.Popen(
                [_python(), "-m", "remocon", "agent"], cwd=ROOT, env=_user_env(),
                stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW)
            while self.child.poll() is None:
                if win32event.WaitForSingleObject(self.stop_event, 1000) == win32event.WAIT_OBJECT_0:
                    self._kill_child()
                    log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} service stopped\n")
                    return
            log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} agent exited ({self.child.returncode})\n")
            # A long run resets the backoff; a crash loop backs off up to a minute.
            backoff = 2 if time.time() - started > 60 else min(backoff * 2, 60)
            if win32event.WaitForSingleObject(self.stop_event, backoff * 1000) == win32event.WAIT_OBJECT_0:
                return


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(RemoconAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(RemoconAgentService)
