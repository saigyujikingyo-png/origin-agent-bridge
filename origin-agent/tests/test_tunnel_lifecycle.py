import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import replace
from pathlib import Path

import psutil
import pytest

from origin_agent.storage import BusyError, file_lock, write_json
from origin_agent.tunnel_lifecycle import (
    Connection,
    Controller,
    Identity,
    LifecycleError,
    OwnershipError,
    Policy,
    allow_start,
    run,
    status,
    stop,
)

FIXTURE = Path(__file__).parent / "fixtures/tunnel_process.py"
PYTHON = str(Path(psutil.Process().exe()).resolve())


@pytest.fixture
def world(tmp_path, monkeypatch):
    # Windows venv Python is a two-process redirector. Use the actual interpreter
    # for the vendor-daemon fixture, retaining this environment's installed libraries.
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(sys.path))
    yield tmp_path
    # Fixture-only cleanup checks creation identity. Never affects installed state.
    for path in (tmp_path / "pids").glob("*.json"):
        value = json.loads(path.read_text())
        try:
            process = psutil.Process(value["pid"])
            if abs(process.create_time() - value["created"]) < 0.001:
                process.terminate()
                process.wait(4)
        except psutil.NoSuchProcess:
            pass
        except psutil.TimeoutExpired:
            assert process.status() == psutil.STATUS_ZOMBIE


def setup(world, settings=None, name=None):
    name = name or "test-" + uuid.uuid4().hex[:10]
    state = world / "state"
    cloud = state / "cloud/accounts" / name
    profiles = cloud / "profiles"
    profiles.mkdir(parents=True)
    executable = PYTHON
    write_json(state / "install.json", {"executable": executable, "version": "fixture"})
    write_json(
        profiles / f"{name}.yaml",
        {"control_plane": {"tunnel_id": "tunnel_abcdef", "api_key": "env:CONTROL_PLANE_API_KEY"}},
    )
    config = cloud / "runtime-config.json"
    write_json(
        config,
        {
            "schema_version": 1,
            "alias": name,
            "profile": name,
            "profile_dir": str(profiles),
            "state_root": str(state),
            "cloud_root": str(cloud),
            "secret_file": str(cloud / "key.dpapi"),
            "tunnel_client": executable,
        },
    )
    mapping = json.loads((world / "mapping.json").read_text()) if (world / "mapping.json").exists() else {}
    mapping[name] = str(profiles)
    write_json(world / "mapping.json", mapping)
    write_json(world / name / "settings.json", settings or {})
    c = Connection.load(config)
    controller = Controller(
        c,
        policy=Policy(
            command_timeout=3, ready_timeout=4, poll=0.05, health_interval=0.1, cleanup_timeout=3, retries=()
        ),
        command=[PYTHON, str(FIXTURE), "--root", str(world)],
    )
    return controller, config


def count(world, alias):
    path = world / alias / "connects.json"
    return json.loads(path.read_text()) if path.exists() else 0


def wait_for(predicate, timeout=4):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(0.04)
    raise AssertionError("fixture did not reach the expected observable state")


def test_delayed_ready_has_one_daemon_and_one_connect(world):
    controller, _ = setup(world, {"ready_after": 0.9})
    daemon = controller.ensure_ready()
    daemons, children = controller.scan()
    assert daemon.live() and len(daemons) == len(children) == 1
    assert count(world, controller.c.alias) == 1
    controller.note("ready", ready=True, healthy=True, daemon=daemon)
    controller.reconcile()
    assert not daemon.live() and not any(p.live() for p in children)


def test_never_registered_alias_connects_once_using_existing_identity(world):
    controller, _ = setup(world)
    original = controller.c.profile_path.read_bytes()
    assert controller.probe() == {"alias_missing": True}
    assert controller.ensure_ready().live()
    assert count(world, controller.c.alias) == 1
    assert controller.c.profile_path.read_bytes() == original


@pytest.mark.parametrize(
    ("override", "error"),
    [
        (
            {"stderr": "alias different-account is not known; run create or connect first", "returncode": 1},
            "command_failed",
        ),
        ({"stderr": "network unavailable", "returncode": 1}, "command_failed"),
        ({"stderr": "unauthorized", "returncode": 1}, "authentication_required"),
        (
            {"stderr": "alias test-absent is not known; run create or connect first", "returncode": 2},
            "command_failed",
        ),
        (
            {
                "stderr": "unauthorized\nalias test-absent is not known; run create or connect first",
                "returncode": 1,
            },
            "authentication_required",
        ),
        ({"stdout": "{broken"}, "invalid_command_output"),
        ({"stdout": "[]"}, "invalid_command_output"),
        ({"stdout": '{"alias_missing":true}'}, "invalid_command_output"),
        (
            {"stdout": '{"alias_missing":true,"profile_name":"different","profile_dir":"wrong"}'},
            "invalid_command_output",
        ),
        ({"stdout": '{"profile_name":"different","profile_dir":"wrong"}'}, "runtime_alias_conflict"),
        ({"stdout": '{"profile_name":"test-absent","profile_dir":"wrong"}'}, "runtime_alias_conflict"),
    ],
)
def test_status_failure_cannot_be_treated_as_alias_absence(world, override, error):
    controller, _ = setup(world, {"status_override": override}, name="test-absent")
    with pytest.raises(LifecycleError, match=error):
        controller.supervise()
    assert count(world, controller.c.alias) == 0
    assert controller.scan() == ([], [])


@pytest.mark.parametrize(
    "failure", ["before_spawn", "after_spawn", "status_fail_after_spawn", "connect_hang", "no_child"]
)
def test_failed_attempt_reconciles_real_children_before_return(world, failure):
    controller, _ = setup(world, {failure: True})
    controller.policy = replace(controller.policy, command_timeout=0.9, ready_timeout=1.2)
    with pytest.raises(LifecycleError):
        controller.supervise()
    assert controller.scan() == ([], [])
    assert count(world, controller.c.alias) == 1
    receipt = json.loads((controller.c.cloud_root / "background-status.json").read_text())
    assert receipt["ready"] is False and receipt["state"] == "failed"


def test_status_failure_before_spawn_is_bounded_and_does_not_connect(world):
    controller, _ = setup(world, {"status_hang": True})
    controller.policy = replace(controller.policy, command_timeout=0.6)
    started = time.monotonic()
    with pytest.raises(LifecycleError, match="command_timeout"):
        controller.supervise()
    assert time.monotonic() - started < 3
    assert count(world, controller.c.alias) == 0


def test_retry_reconciles_previous_spawn_not_accumulates(world):
    controller, _ = setup(world, {"after_spawn": True})
    controller.policy = replace(controller.policy, retries=(0.05,))
    with pytest.raises(LifecycleError):
        controller.supervise()
    assert count(world, controller.c.alias) == 2
    assert controller.scan() == ([], [])
    records = [json.loads(p.read_text()) for p in (world / "pids").glob("*.json")]
    assert sum(p["role"] == "run" for p in records) == 2
    events = json.loads((world / controller.c.alias / "connect_events.json").read_text())
    assert all(event["previous_live"] == [] for event in events)


def test_adopts_healthy_existing_owner_without_connect(world):
    first, config = setup(world)
    old = first.ensure_ready()
    second = Controller(Connection.load(config), command=first.command, policy=first.policy)
    assert second.ensure_ready().pid == old.pid
    assert count(world, first.c.alias) == 1


def test_two_profiles_and_unrelated_frontend_are_preserved(world):
    first, config = setup(world)
    second, _ = setup(world)
    a, b = first.ensure_ready(), second.ensure_ready()
    unrelated = subprocess.Popen(
        [PYTHON, str(FIXTURE), "--root", str(world), "serve"],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    wait_for(lambda: (world / "pids" / f"{unrelated.pid}.json").exists())
    stop(config)
    assert not a.live() and b.live() and unrelated.poll() is None
    assert first.c.intent()["enabled"] is False


def test_duplicate_scoped_daemons_are_reconciled_before_new_connect(world):
    controller, _ = setup(world)
    first = controller.ensure_ready()
    controller.command_json(
        [
            "runtimes",
            "connect",
            "--alias",
            controller.c.alias,
            "--profile",
            controller.c.profile,
            "--profile-dir",
            str(controller.c.profile_dir),
        ],
        observe=True,
    )
    wait_for(lambda: len(controller.scan()[0]) == 2)
    assert controller.ensure_ready().pid != first.pid
    assert len(controller.scan()[0]) == 1
    assert count(world, controller.c.alias) == 3


def test_saved_lineage_reconciles_orphan_without_harming_job(world):
    controller, _ = setup(world, {"job_child": True})
    daemon = controller.ensure_ready()
    _, children = controller.scan()
    jobs = wait_for(
        lambda: [
            json.loads(p.read_text())
            for p in (world / "pids").glob("*.json")
            if json.loads(p.read_text())["role"] == "supervise"
        ]
    )
    controller.terminate(daemon)
    assert all(p.live() for p in children)
    controller.reconcile()
    assert not any(p.live() for p in children)
    assert all(psutil.pid_exists(p["pid"]) for p in jobs)


def test_missing_registry_after_spawn_does_not_hide_processes(world):
    controller, _ = setup(world, {"missing_registry": True})
    controller.policy = replace(controller.policy, ready_timeout=1)
    with pytest.raises(LifecycleError, match="readiness_timeout"):
        controller.supervise()
    assert count(world, controller.c.alias) == 1 and controller.scan() == ([], [])


def test_reused_pid_token_cannot_terminate_live_process(world):
    controller, _ = setup(world)
    daemon = controller.ensure_ready()
    controller.terminate(replace(daemon, created=daemon.created - 10))
    assert daemon.live()


def test_scope_lock_is_shared_by_alias_config_paths(world):
    controller, config = setup(world)
    alternative = world / "candidate.json"
    alternative.write_bytes(config.read_bytes())
    other = Connection.load(alternative)
    assert other.lock == controller.c.lock
    with file_lock(controller.c.lock, timeout=0):
        with pytest.raises(BusyError):
            with file_lock(other.lock, timeout=0):
                pytest.fail("second owner acquired the same scope")


def test_stale_success_and_dead_supervisor_are_not_ready(world):
    controller, config = setup(world)
    daemon = controller.ensure_ready()
    value = controller.note("ready", ready=True, healthy=True, daemon=daemon)
    value["valid_until"] = time.time() - 1
    write_json(controller.c.cloud_root / "supervisor-state.json", value)
    assert status(config)["state"] == "stale" and not status(config)["ready"]
    value["valid_until"] = time.time() + 60
    value["supervisor"]["created"] -= 10
    write_json(controller.c.cloud_root / "supervisor-state.json", value)
    assert status(config)["state"] == "stale"


def test_disabled_intent_stays_stopped_until_explicit_start(world):
    controller, config = setup(world)
    stop(config)
    assert controller.supervise()["state"] == "stopped"
    assert count(world, controller.c.alias) == 0
    allow_start(config)
    assert controller.ensure_ready().live()


def test_health_failure_invalidates_old_success_and_cleans_up(world):
    controller, config = setup(world)
    daemon = controller.ensure_ready()
    controller.note("ready", ready=True, healthy=True, daemon=daemon)
    write_json(world / controller.c.alias / "settings.json", {"status_fail": True})
    with pytest.raises(LifecycleError):
        controller.supervise()
    assert not status(config)["healthy"]
    assert not daemon.live() and controller.scan() == ([], [])


def test_conflicting_profile_directory_fails_closed(world):
    controller, _ = setup(world)
    daemon = controller.ensure_ready()
    conflict = replace(controller.c, profile_dir=world / "elsewhere")
    with pytest.raises(OwnershipError):
        other = Controller(conflict, command=controller.command, policy=controller.policy)
        other.ensure_ready()
    assert daemon.live() and count(world, controller.c.alias) == 1


def test_identity_contains_creation_parent_and_executable():
    identity = Identity.capture(psutil.Process(), "fixture")
    assert identity.pid == os.getpid() and identity.created > 0 and Path(identity.exe).is_absolute()
    assert identity.parent_pid > 0 and identity.parent_created is not None


def spawn_controller(world, config):
    return subprocess.Popen(
        [PYTHON, str(FIXTURE), "--root", str(world), "controller", "--config", str(config)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def test_real_supervisor_singleton_cooperative_stop_and_crash_adoption(world):
    controller, config = setup(world)
    owner = spawn_controller(world, config)
    wait_for(lambda: status(config).get("ready"), timeout=8)
    assert run(config)["state"] == "already_supervised"
    daemon = controller.scan()[0][0]
    owner.kill()
    owner.wait(3)
    assert status(config)["state"] == "stale" and daemon.live()
    replacement = spawn_controller(world, config)
    wait_for(lambda: status(config).get("ready"), timeout=8)
    assert count(world, controller.c.alias) == 1
    assert stop(config)["state"] == "stopped"
    replacement.wait(3)
    assert replacement.returncode == 0 and not daemon.live()


def test_continuous_health_failure_is_detected_by_real_supervisor(world):
    controller, config = setup(world)
    owner = spawn_controller(world, config)
    wait_for(lambda: status(config).get("ready"), timeout=8)
    write_json(world / controller.c.alias / "settings.json", {"status_fail": True})
    owner.wait(8)
    assert owner.returncode != 0
    assert status(config)["state"] == "failed" and not status(config)["ready"]
    assert controller.scan() == ([], [])


def test_unknown_orphan_is_preserved_and_blocks_new_spawn(world):
    controller, config = setup(world)
    daemon = controller.ensure_ready()
    _, children = controller.scan()
    controller.terminate(daemon)
    controller.ledger_path.unlink()
    independent = Controller(Connection.load(config), policy=controller.policy, command=controller.command)
    with pytest.raises(OwnershipError, match="unproven_orphan"):
        independent.ensure_ready()
    assert all(p.live() for p in children) and count(world, controller.c.alias) == 1


def test_cleanup_refusal_resumes_every_proven_producer(world, monkeypatch):
    controller, _ = setup(world)
    controller.ensure_ready()
    daemons, children = controller.scan()

    def refuse(_identity):
        raise OwnershipError("simulated_stop_refusal")

    monkeypatch.setattr(controller, "terminate", refuse)
    with pytest.raises(OwnershipError, match="stop_refusal"):
        controller.reconcile()
    assert all(
        p.live() and psutil.Process(p.pid).status() != psutil.STATUS_STOPPED for p in daemons + children
    )


def test_readiness_rechecks_child_and_parent_creation_after_status(world):
    controller, _ = setup(world)
    controller.ensure_ready()
    daemons, children = controller.scan()
    observed = controller.probe()
    assert not controller.verified_ready(observed, daemons, [replace(children[0], parent_created=0)])
    controller.terminate(children[0])
    assert not controller.verified_ready(observed, daemons, children)


def test_one_resume_failure_does_not_skip_other_suspended_producers(world, monkeypatch):
    controller, _ = setup(world)
    controller.ensure_ready()
    daemons, children = controller.scan()
    original_resume = psutil.Process.resume
    attempted = []

    def resume(process):
        attempted.append(process.pid)
        if process.pid == daemons[0].pid:
            raise psutil.AccessDenied(process.pid)
        return original_resume(process)

    def refuse(_identity):
        raise OwnershipError("simulated_stop_refusal")

    monkeypatch.setattr(controller, "terminate", refuse)
    monkeypatch.setattr(psutil.Process, "resume", resume)
    try:
        with pytest.raises(OwnershipError, match="resume_unconfirmed"):
            controller.reconcile()
        assert set(attempted) == {p.pid for p in daemons + children}
        assert all(psutil.Process(p.pid).status() != psutil.STATUS_STOPPED for p in children)
    finally:
        for p in daemons:
            if p.live():
                original_resume(psutil.Process(p.pid))
