"""deploy/loadtest/seed.py -- the pure helpers (targets, guard), no network."""
import importlib.util
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PATH = _ROOT / "deploy" / "loadtest" / "seed.py"
sys.path.insert(0, str(_ROOT / "deploy" / "local"))
_spec = importlib.util.spec_from_file_location("lt_seed", _PATH)
lt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lt)


def test_team_names_round_trip():
    assert lt.team_name(7) == "lt-0007"
    assert lt.is_loadtest_name("lt-0300")
    assert not lt.is_loadtest_name("lt-1")
    assert not lt.is_loadtest_name("Kékéli Defenders")
    assert not lt.is_loadtest_name(None)


def test_static_flags_only_string_entries(tmp_path):
    a = tmp_path / "web" / "a"
    b = tmp_path / "web" / "b"
    c = tmp_path / "web" / "c"
    for d in (a, b, c):
        d.mkdir(parents=True)
    a.joinpath("challenge.yml").write_text(
        "name: a\nflags:\n  - NCTF{first}\n  - NCTF{second}\n"
    )
    b.joinpath("challenge.yml").write_text(
        "name: b\nflags:\n  - type: team_hmac\n    content: web-b\n"
    )
    c.joinpath("challenge.yml").write_text("name: c\n")
    assert lt.static_flags([str(a), str(b), str(c), str(tmp_path / "nope")]) == {
        "a": "NCTF{first}"
    }


def test_targets_split_visible_challenges():
    chals = [
        {"id": 1, "name": "a", "type": "dynamic", "state": "visible"},
        {"id": 2, "name": "b", "type": "team_instance", "state": "visible"},
        {"id": 3, "name": "a2", "type": "dynamic", "state": "hidden"},
        {"id": 4, "name": "unknown", "type": "dynamic", "state": "visible"},
    ]
    flags, inst = lt.targets(chals, {"a": "NCTF{a}", "a2": "NCTF{a2}", "b": "NCTF{b}"})
    assert flags == [{"challenge_id": 1, "flag": "NCTF{a}", "name": "a"}]
    assert inst == [2]


def test_guard_refuses_remote_real_event_and_future_start():
    now = 1_000_000
    assert lt.guard("http://localhost:8000", 0, "", now, False, 20) is None
    assert "allow-remote" in lt.guard("https://ctf.tg", 0, "", now, False, 20)
    assert lt.guard("https://ctf.tg", 5, "", now, True, 20) is None
    assert "epreuve" in lt.guard("https://ctf.tg", 21, "", now, True, 20)
    assert "futur" in lt.guard(
        "http://localhost:8000", 0, str(now + 60), now, False, 20
    )
    assert lt.guard("http://localhost:8000", 0, str(now - 60), now, False, 20) is None
