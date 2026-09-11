import pytest

from origin_agent.planning import load_plan
from origin_agent.programs import OriginProgram, prepare_program
from origin_agent.session_native import SessionEngine
from origin_agent.sessions import (
    SessionCommand,
    interrupted_session,
    prepare_session,
    read_session,
    session_path,
)
from origin_agent.storage import read_json, write_json


def test_control_retry_is_idempotent_but_request_id_cannot_change_content(store):
    command = SessionCommand(action="open", request_id="experiment-1", expected_revision=0)
    first = prepare_session(store, command)
    assert prepare_session(store, command) == first
    with pytest.raises(ValueError, match="different content"):
        prepare_session(store, command.model_copy(update={"title": "different"}))
    assert load_plan(store, first["plan_id"])["kind"] == "session"


def test_tampered_session_plan_is_not_repaired_by_retry(store):
    command = SessionCommand(action="open", request_id="experiment-2", expected_revision=0)
    prepared = prepare_session(store, command)
    path = store.path("plans", prepared["plan_id"]) / "plan.json"
    value = read_json(path)
    value["workflow"]["visible"] = True
    write_json(path, value)
    with pytest.raises(ValueError, match="integrity"):
        prepare_session(store, command)


def test_stale_revision_fails_before_origin_activation(store, monkeypatch):
    identifier = "a" * 32
    write_json(session_path(store, identifier), {"revision": 2, "state": "ready"})
    command = SessionCommand(
        action="checkpoint", request_id="stale", session_id=identifier, expected_revision=1
    )
    prepared = prepare_session(store, command)
    monkeypatch.setattr(
        "origin_agent.session_native.connect_origin", lambda *_: pytest.fail("Origin was started")
    )
    engine = SessionEngine(store)
    with pytest.raises(ValueError, match="Stale session revision"):
        engine.execute("b" * 32, prepared["plan_id"])
    assert read_json(session_path(store, identifier))["revision"] == 2


def test_active_program_cannot_replace_session_project(store, tmp_path):
    project = tmp_path / "input.opju"
    project.write_bytes(b"test snapshot")
    program = prepare_program(
        store,
        OriginProgram(
            title="bad replacement",
            language="python",
            code="pass",
            project_path=str(project),
        ),
    )
    with pytest.raises(ValueError, match="active project"):
        prepare_session(
            store,
            SessionCommand(
                action="execute",
                request_id="replacement",
                session_id="a" * 32,
                expected_revision=1,
                program_plan_id=program["plan_id"],
            ),
        )


def test_interrupt_recovers_before_image_without_advancing_revision(store):
    identifier, job = "a" * 32, "b" * 32
    path = session_path(store, identifier)
    write_json(
        path,
        {
            "revision": 4,
            "state": "executing",
            "active_job": job,
            "checkpoint_path": "old.opju",
            "checkpoint_sha256": "oldhash",
            "recovery_path": "before.opju",
            "recovery_sha256": "newhash",
        },
    )
    interrupted_session(store, {"session_id": identifier}, job)
    state = read_json(path)
    assert (state["revision"], state["state"], state["checkpoint_path"], state["checkpoint_sha256"]) == (
        4,
        "suspended",
        "before.opju",
        "newhash",
    )
    interrupted_session(store, {"session_id": identifier}, job)
    assert read_json(path) == state


def test_old_worker_cannot_overwrite_new_owner_on_shutdown(store):
    identifier = "a" * 32
    state = {"worker_token": "new-owner", "revision": 7, "state": "ready"}
    write_json(session_path(store, identifier), state)
    engine = SessionEngine(store)
    engine.runtime = {"op": object()}
    engine.current = identifier
    engine.suspend()
    assert engine.current is None
    assert read_json(session_path(store, identifier)) == state


def test_dead_supervisor_cannot_start_a_session(store, monkeypatch):
    command = SessionCommand(action="open", request_id="dead-parent", expected_revision=0)
    plan = prepare_session(store, command)
    monkeypatch.setattr(
        "origin_agent.session_native.connect_origin", lambda *_: pytest.fail("Origin was started")
    )
    engine = SessionEngine(store, parent_alive=lambda: False)
    with pytest.raises(RuntimeError, match="supervisor stopped"):
        engine.execute("b" * 32, plan["plan_id"])
    assert not session_path(store, plan["session_id"]).exists()


def test_session_metadata_is_bounded_without_truncating_stored_state(store):
    identifier = "a" * 32
    state = {
        "project_index": {
            "pages": [{"name": str(i), "sheets": [{"name": str(j)} for j in range(30)]} for i in range(80)],
            "graphs": [],
        },
        "worker_token": "internal",
    }
    path = session_path(store, identifier)
    write_json(path, state)
    public = read_session(store, identifier)
    assert "worker_token" not in public
    index = public["project_index"]
    assert index["page_count"] == 80 and index["truncated"]
    assert len(index["pages"]) == 40 and len(index["pages"][0]["sheets"]) == 20
    assert read_json(path) == state
