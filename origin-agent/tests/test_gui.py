import copy
from types import SimpleNamespace

import pytest

from origin_agent.gui import GuiCommand, resolve_target
from origin_agent.gui_native import NativeGui
from origin_agent.origin_runtime import release_terminated_origin
from origin_agent.session_native import SessionEngine
from origin_agent.sessions import SessionCommand, prepare_session, read_session, session_path
from origin_agent.storage import read_json, write_json


def observation():
    return {
        "process": {"pid": 123, "created": 1.0},
        "observed_at": 100,
        "windows": [{"id": "w:1", "text": "Origin", "enabled": True}],
        "targets": [{"id": "c:2", "text": "Apply", "enabled": True, "kind": "control"}],
        "blocked": False,
        "truncated": False,
        "query": "",
    }


@pytest.mark.parametrize("change", ["process", "modal", "text", "missing", "disabled", "expired"])
def test_changed_gui_target_or_context_never_receives_input(change):
    previous = observation()
    current = copy.deepcopy(previous)
    if change == "process":
        current["process"]["created"] = 2.0
    elif change == "modal":
        current["windows"].append({"id": "w:3", "text": "Dialog", "enabled": True})
    elif change == "text":
        current["targets"][0]["text"] = "Delete"
    elif change == "missing":
        current["targets"] = []
    elif change == "disabled":
        previous["targets"][0]["enabled"] = current["targets"][0]["enabled"] = False
    with pytest.raises(ValueError):
        resolve_target(previous, current, "c:2", now=300 if change == "expired" else 110)


def test_gui_contract_rejects_guessed_input_and_hidden_text():
    with pytest.raises(ValueError, match="recent observation"):
        GuiCommand(action="invoke", target_id="1")
    with pytest.raises(ValueError, match="text is required"):
        GuiCommand(action="observe", text="secret")
    with pytest.raises(ValueError, match="NUL"):
        GuiCommand(action="set_text", observation_id="a" * 32, target_id="c:2", text="a\x00b")


def test_duplicate_accessible_ids_are_rejected_before_input():
    view = observation()
    view["targets"].append(dict(view["targets"][0]))
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_target(view, view, "c:2", now=110)


def active_gui(store):
    identifier = "a" * 32
    state = {
        "session_id": identifier,
        "revision": 3,
        "state": "gui",
        "worker_token": "owner",
        "gui_transaction": {"path": "before.opju", "sha256": "hash"},
        "checkpoint_id": "c" * 32,
        "gui_observation_id": "d" * 32,
        "origin_pid": 123,
    }
    write_json(session_path(store, identifier), state)
    engine = SessionEngine(store)
    engine.token, engine.current = "owner", identifier
    engine.runtime = {"op": object(), "origin_pid": 123, "origin_created": 1.0, "engine": {}}
    return identifier, engine


def test_gui_blocks_com_and_project_switch_before_save(store):
    identifier, engine = active_gui(store)
    request = SessionCommand(
        action="checkpoint", request_id="test", session_id=identifier, expected_revision=3
    )
    plan = prepare_session(store, request)
    with pytest.raises(ValueError, match="active GUI transaction"):
        engine.execute("b" * 32, plan["plan_id"])
    with pytest.raises(ValueError, match="active GUI transaction"):
        engine.suspend()


@pytest.mark.parametrize("screenshot", [False, True])
def test_observation_while_modal_does_not_call_com_and_advances_revision(store, monkeypatch, screenshot):
    identifier, engine = active_gui(store)
    observed = observation()
    observed["blocked"] = True

    class Backend:
        def __init__(self, _):
            pass

        def observe(self, _):
            return observed

        def capture(self, *_):
            raise OSError("screen grab failed")

    monkeypatch.setattr("origin_agent.gui_session.NativeGui", Backend)
    request = SessionCommand(
        action="gui",
        request_id="observe",
        session_id=identifier,
        expected_revision=3,
        gui=GuiCommand(action="observe", screenshot=screenshot),
    )
    plan = prepare_session(store, request)
    job = "b" * 32
    store.path("jobs", job).mkdir()
    result = engine.execute(job, plan["plan_id"])
    assert result["revision"] == 4
    assert read_session(store, identifier)["gui_transaction_open"]
    assert "gui_transaction" not in read_session(store, identifier)
    manifest = read_json(store.path("jobs", job) / "manifest.json")
    assert not manifest["verification"]["project_saved"]
    assert manifest["gui"]["blocked"]
    assert ("screenshot_error" in manifest["gui"]) == screenshot
    assert not manifest["verification"]["screenshot_captured"]
    request = request.model_copy(
        update={"request_id": "commit", "expected_revision": 4, "gui": GuiCommand(action="commit")}
    )
    plan = prepare_session(store, request)
    with pytest.raises(ValueError, match="Close the Origin dialog"):
        engine.execute("e" * 32, plan["plan_id"])
    assert read_session(store, identifier)["revision"] == 4


def test_gui_failure_invalidates_observation_without_com_rollback(store, monkeypatch):
    identifier, engine = active_gui(store)
    observed = observation()
    directory = store.path("jobs", "d" * 32)
    directory.mkdir()
    write_json(directory / "gui-private.json", observed)

    class Backend:
        def __init__(self, _):
            pass

        def observe(self, _):
            return observed

        def invoke(self, _):
            raise RuntimeError("dispatch outcome unknown")

    monkeypatch.setattr("origin_agent.gui_session.NativeGui", Backend)
    monkeypatch.setattr("origin_agent.gui.time.time", lambda: 110)
    request = SessionCommand(
        action="gui",
        request_id="input",
        session_id=identifier,
        expected_revision=3,
        gui=GuiCommand(action="invoke", observation_id="d" * 32, target_id="c:2"),
    )
    plan = prepare_session(store, request)
    job = "b" * 32
    store.path("jobs", job).mkdir()
    with pytest.raises(RuntimeError, match="outcome unknown"):
        engine.execute(job, plan["plan_id"])
    state = read_session(store, identifier)
    assert state["state"] == "gui" and state["revision"] == 4 and state["gui_observation_id"] is None


def test_gui_worker_shutdown_does_not_enter_modal_com_save(store):
    identifier, engine = active_gui(store)
    before = read_json(session_path(store, identifier))
    engine.shutdown()
    assert engine.runtime is None
    assert read_json(session_path(store, identifier)) == before


@pytest.mark.parametrize("error_code", [-2147220991, -2146233083])
def test_transient_destroyed_dialog_retries_observation_only(monkeypatch, error_code):
    backend = NativeGui.__new__(NativeGui)
    calls = []

    class Gone(Exception):
        hresult = error_code

    def observe(query):
        calls.append(query)
        if len(calls) == 1:
            raise Gone("dialog disappeared during UIA enumeration")
        return observation()

    monkeypatch.setattr(backend, "_observe", observe)
    monkeypatch.setattr("origin_agent.gui_native.time.sleep", lambda _: None)
    assert backend.observe("Window") == observation()
    assert calls == ["Window", "Window"]
    monkeypatch.setattr(backend, "_observe", lambda _: (_ for _ in ()).throw(Gone()))
    with pytest.raises(Gone):
        backend.observe()


def test_dead_connection_reset_never_discards_a_live_origin(monkeypatch):
    import psutil

    wrapper = SimpleNamespace(_app=object())

    def broken_detach():
        raise RuntimeError("server has terminated")

    runtime = {
        "origin_pid": 123,
        "origin_created": 1.0,
        "op": SimpleNamespace(po=wrapper, detach=broken_detach),
    }
    monkeypatch.setattr(psutil, "Process", lambda _: SimpleNamespace(create_time=lambda: 1.0))
    with pytest.raises(RuntimeError, match="process is alive"):
        release_terminated_origin(runtime)
    assert wrapper._app is not None

    def gone(_):
        raise psutil.NoSuchProcess(123)

    monkeypatch.setattr(psutil, "Process", gone)
    release_terminated_origin(runtime)
    assert wrapper._app is None
