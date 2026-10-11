"""Smoke tests: the package imports, config bootstraps, the servers bind and
answer, and service files render — on whatever OS runs the tests."""

import json
import urllib.request

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("REMOCON_HOME", str(tmp_path / "remocon"))
    monkeypatch.delenv("REMOCON_CONFIG", raising=False)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    (tmp_path / "claude").mkdir()
    return tmp_path


def _free_port():
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_config_bootstrap_and_import(tmp_path):
    from remocon import config
    cfg = config.load_config()
    assert len(cfg["secret"]) == 64 and cfg["machines"] == []
    legacy = tmp_path / "csm.config.json"
    legacy.write_text(json.dumps({"secret": "s" * 64, "machines": [{"id": "pc", "localPort": 9101}],
                                  "agent": {"host": "127.0.0.1", "port": 1},
                                  "control": {"host": "127.0.0.1", "port": 2}}))
    cfg = config.import_legacy(legacy)
    assert cfg["secret"] == "s" * 64 and cfg["machines"][0]["id"] == "pc"
    assert config.load_config() == cfg


def test_legacy_state_files_are_adopted(tmp_path):
    from remocon.agent import claude_store
    (tmp_path / "claude" / ".csm-session-names.json").write_text('{"abc": "my session"}')
    assert claude_store.session_names() == {"abc": "my session"}


def test_hub_and_agent_answer():
    import threading
    from remocon import config
    from remocon.agent import server as agent_server
    from remocon.hub import server as hub_server
    cfg = config.load_config()
    cfg["agent"]["port"], cfg["control"]["port"] = _free_port(), _free_port()
    config.save_config(cfg)
    a = agent_server.serve(cfg)
    h = hub_server.serve(cfg)
    for srv in (a, h):
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{cfg['control']['port']}"
        html = urllib.request.urlopen(base + "/").read().decode()
        assert "/assets/app.js" in html
        assert urllib.request.urlopen(base + "/assets/app.css").status == 200
        machines = json.load(urllib.request.urlopen(base + "/api/machines"))["machines"]
        mid = machines[0]["id"]
        health = json.load(urllib.request.urlopen(f"{base}/api/m/{mid}/health"))
        assert health["ok"] is True
        folders = json.load(urllib.request.urlopen(f"{base}/api/m/{mid}/folders?codex=0"))
        assert folders["folders"] == []
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/assets/../../config.py")
    finally:
        a.shutdown()
        h.shutdown()


def test_service_files_render():
    from remocon.host import service
    assert "com.remocon.up" in service.render_plist("up")
    unit = service.render_unit("agent")
    assert "-m remocon agent" in unit and "Restart=always" in unit


def test_cli_parses():
    from remocon.cli import build_parser
    a = build_parser().parse_args(["deploy", "pc", "10.0.0.2", "alice", "--ssh-port", "2222"])
    assert (a.id, a.host, a.ssh_user, a.ssh_port) == ("pc", "10.0.0.2", "alice", 2222)
