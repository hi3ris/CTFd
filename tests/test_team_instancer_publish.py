"""INSTANCER_PUBLISH selects how a spawned container is exposed: through frp
on the arena (production) or straight on the Docker host (local validation).
The frp path is exercised at the rehearsal; this pins the switch itself."""
import importlib
import os


def _reload_settings(monkeypatch, **env):
    for k in ("INSTANCER_PUBLISH", "INSTANCER_OLLAMA_MODEL", "DOCKER_HOST"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    from CTFd.plugins.team_instancer import settings
    return importlib.reload(settings)


def test_default_is_frp_on_arena(monkeypatch):
    s = _reload_settings(monkeypatch)
    assert s.PUBLISH == "frp" and s.uses_frp()
    assert s.network_driver() == "overlay"
    assert s.port_binding(28001) == ("127.0.0.1", 28001)
    assert s.extra_hosts() == {}
    assert s.OLLAMA_MODEL_OVERRIDE == ""


def test_direct_mode_publishes_on_host_bridge(monkeypatch):
    s = _reload_settings(monkeypatch, INSTANCER_PUBLISH="direct", INSTANCER_OLLAMA_MODEL="llama3.2:3b")
    assert not s.uses_frp()
    assert s.network_driver() == "bridge"
    assert s.port_binding(28001) == ("0.0.0.0", 28001)
    assert s.extra_hosts() == {"host.docker.internal": "host-gateway"}
    assert s.OLLAMA_MODEL_OVERRIDE == "llama3.2:3b"


def test_unknown_mode_is_rejected_at_import(monkeypatch):
    import pytest
    with pytest.raises(RuntimeError):
        _reload_settings(monkeypatch, INSTANCER_PUBLISH="magic")
    _reload_settings(monkeypatch)  # restore for other tests


def test_frpc_calls_are_skipped_in_direct_mode(monkeypatch):
    _reload_settings(monkeypatch, INSTANCER_PUBLISH="direct")
    from CTFd.plugins.team_instancer import backend
    importlib.reload(backend)
    called = []
    monkeypatch.setattr(backend, "_frpc_request", lambda *a, **k: called.append(a))
    backend._frpc_add("t1-c1", 28001)
    backend._frpc_remove("t1-c1")
    assert called == []
    _reload_settings(monkeypatch)
    importlib.reload(backend)
