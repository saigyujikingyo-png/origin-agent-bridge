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
    quiesce_legacy_wrapper,
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
    # Freeze exact fixture producers before enumerating children. PID publication
    # can lag process launch; never let a failed assertion leak a late frontend.
    scoped = []
    for process in psutil.process_iter(["cmdline"]):
        try:
            argv = process.info["cmdline"] or []
            if str(FIXTURE) not in argv or "--root" not in argv:
                continue
            if Path(argv[argv.index("--root") + 1]).resolve() != tmp_path.resolve():
                continue
            if Path(process.exe()).resolve() != Path(PYTHON):
                continue
            scoped.append((process, process.create_time()))
            if "run" in argv or "controller" in argv:
                process.suspend()
        except psutil.NoSuchProcess:
            continue
    # With producers frozen, one more enumeration captures their final children.
    for process in psutil.process_iter(["cmdline"]):
        try:
            argv = process.info["cmdline"] or []
            if (
                str(FIXTURE) in argv
                and "--root" in argv
                and Path(argv[argv.index("--root") + 1]).resolve() == tmp_path.resolve()
                and Path(process.exe()).resolve() == Path(PYTHON)
            ):
                scoped.append((process, process.create_time()))
        except psutil.NoSuchProcess:
            pass
    for process, created in scoped:
        try:
            if process.is_running() and process.create_time() == created:
                process.kill()
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
            "schema_version": 2,
            "client_state_dir": str(cloud / "tunnel-state"),
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
    c.secret_file.write_bytes(b"encrypted-fixture-revision-one")
    controller = Controller(
        c,
        policy=Policy(
            command_timeout=3,
            ready_timeout=4,
            poll=0.05,
            health_interval=0.1,
            cleanup_timeout=3,
            retries=(),
            recovery_delays=(),
        ),
        command=[PYTHON, str(FIXTURE), "--root", str(world)],
        remote_probe=lambda *_args: {"state": "online", "reason": None, "idle": True},
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
    if error == "authentication_required":
        assert controller.supervise()["state"] == "blocked"
        assert controller.authentication_blocked()
    else:
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
    with pytest.raises(OwnershipError, match="runtime_registry_identity_conflict"):
        controller.supervise()
    assert count(world, controller.c.alias) == 1
    assert len(controller.scan()[0]) == 1


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


def test_legacy_wrapper_with_live_producer_child_refuses_quiescence_and_resumes(world):
    controller, _ = setup(world)
    wrapper = controller.ensure_ready()
    _, children = controller.scan()
    with pytest.raises(OwnershipError, match="legacy_wrapper_child_in_flight"):
        quiesce_legacy_wrapper(wrapper)
    assert wrapper.live() and psutil.Process(wrapper.pid).status() != psutil.STATUS_STOPPED
    assert all(child.live() for child in children)


def test_legacy_wrapper_without_child_is_frozen_before_exit(world):
    wrapper = subprocess.Popen(
        [PYTHON, str(FIXTURE), "--root", str(world), "serve"],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    wait_for(lambda: (world / "pids" / f"{wrapper.pid}.json").exists())
    owner = Identity.capture(psutil.Process(wrapper.pid), "legacy_wrapper")
    quiesce_legacy_wrapper(owner)
    wrapper.wait(3)
    assert not owner.live()


def test_expired_failure_reports_dead_supervision_without_discarding_cause(world):
    controller, config = setup(world)
    value = controller.note(
        "unknown",
        reason="reconciliation_failed",
        primary_error={"code": "command_timeout", "phase": "status"},
        cleanup_error={"code": "producer_quiesce_timeout", "phase": "reconcile"},
    )
    value["valid_until"] = 1
    value["supervisor"]["created"] -= 100
    write_json(controller.c.cloud_root / "supervisor-state.json", value)
    observed = status(config)
    assert observed["observation_fresh"] is False
    assert observed["supervisor_alive"] is False
    assert observed["primary_error"]["code"] == "command_timeout"
    assert observed["cleanup_error"]["code"] == "producer_quiesce_timeout"


def test_live_owner_survives_transient_probe_failure_and_recovers(world, monkeypatch):
    from origin_agent.tunnel_lifecycle import StopRequested

    controller, config = setup(world)
    daemon = controller.ensure_ready()
    controller.policy = replace(controller.policy, recovery_delays=(0.01,), jitter=0)
    original_probe = controller.probe
    original_note = controller.note
    sequence = []
    failures = 0

    def probe(timeout=None):
        nonlocal failures
        if failures < 2:
            failures += 1
            controller.phase = "status"
            raise LifecycleError("command_timeout")
        return original_probe(timeout)

    def note(state, **kwargs):
        sequence.append(state)
        value = original_note(state, **kwargs)
        if state == "degraded":
            assert daemon.live()
            assert count(world, controller.c.alias) == 1
        if state == "ready":
            assert failures == 2 and daemon.live()
            raise StopRequested("stop_requested")
        return value

    monkeypatch.setattr(controller, "probe", probe)
    monkeypatch.setattr(controller, "note", note)
    assert controller.supervise()["state"] == "stopped"
    assert sequence[:3] == ["degraded", "degraded", "ready"]
    assert count(world, controller.c.alias) == 1
    assert not status(config)["ready"]


def test_network_outage_outlives_fast_retry_budget_and_recovers(world, monkeypatch):
    from origin_agent.tunnel_lifecycle import StopRequested

    controller, _ = setup(world)
    controller.policy = replace(controller.policy, recovery_delays=(0.01,), jitter=0)
    original_probe, original_note = controller.probe, controller.note
    failures = 0

    def probe(timeout=None):
        nonlocal failures
        if failures < 3:
            failures += 1
            controller.phase = "status"
            raise LifecycleError("network_unavailable")
        return original_probe(timeout)

    def note(state, **kwargs):
        result = original_note(state, **kwargs)
        if state == "ready":
            assert failures == 3
            raise StopRequested("stop_requested")
        return result

    monkeypatch.setattr(controller, "probe", probe)
    monkeypatch.setattr(controller, "note", note)
    assert controller.supervise()["state"] == "stopped"
    assert count(world, controller.c.alias) == 1


def test_cleanup_failure_preserves_both_allowlisted_causes(world, monkeypatch):
    controller, config = setup(world)

    def fail_probe(timeout=None):
        controller.phase = "status"
        raise LifecycleError("network_unavailable")

    def refuse():
        raise OwnershipError("producer_quiesce_timeout")

    monkeypatch.setattr(controller, "probe", fail_probe)
    monkeypatch.setattr(controller, "reconcile", refuse)
    with pytest.raises(OwnershipError, match="producer_quiesce_timeout"):
        controller.supervise()
    result = status(config)
    assert result["primary_error"] == {"code": "network_unavailable", "phase": "status"}
    assert result["cleanup_error"] == {"code": "producer_quiesce_timeout", "phase": "reconcile"}


def test_diagnostics_never_publish_arbitrary_exception_text(world, monkeypatch):
    controller, config = setup(world)

    def fail():
        raise RuntimeError("sk-fixture-sensitive-material https://example.invalid/?secret=value")

    monkeypatch.setattr(controller, "ensure_ready", fail)
    with pytest.raises(LifecycleError, match="supervisor_error"):
        controller.supervise()
    for name in ("supervisor-state.json", "background-status.json", "connection-events.json"):
        text = (controller.c.cloud_root / name).read_text()
        assert "sensitive" not in text and "secret=" not in text
    assert status(config)["primary_error"]["code"] == "supervisor_error"


def test_child_state_root_overrides_inherited_global_registry(world, monkeypatch):
    controller, _ = setup(world)
    foreign = world / "foreign-registry"
    foreign.mkdir()
    sentinel = foreign / "processes.yaml"
    sentinel.write_bytes(b"unrelated old client registry")
    monkeypatch.setenv("TUNNEL_CLIENT_STATE_DIR", str(foreign))
    daemon = controller.ensure_ready()
    environment = psutil.Process(daemon.pid).environ()
    assert Path(environment["TUNNEL_CLIENT_STATE_DIR"]) == controller.c.client_state_dir
    assert sentinel.read_bytes() == b"unrelated old client registry"
    assert len(controller.scan()[0]) == 1


def test_mismatched_registry_preserves_owner_and_blocks_second_connect(world):
    controller, _ = setup(world)
    daemon = controller.ensure_ready()
    registry = world / controller.c.alias / "registry.json"
    value = json.loads(registry.read_text())
    value["pid"] = 2147483647
    write_json(registry, value)
    with pytest.raises(OwnershipError, match="runtime_registry_identity_conflict"):
        controller.supervise()
    assert daemon.live()
    assert count(world, controller.c.alias) == 1


def test_v2_config_rejects_shared_or_redirected_state_root(world):
    controller, config = setup(world)
    value = json.loads(config.read_text())
    value["client_state_dir"] = str(world / "shared-vendor")
    write_json(config, value)
    with pytest.raises(LifecycleError, match="invalid_client_state_directory"):
        Connection.load(config)


def test_legacy_config_cannot_silently_restart_shared_vendor_state(world):
    controller, config = setup(world)
    value = json.loads(config.read_text())
    value["schema_version"] = 1
    value.pop("client_state_dir")
    write_json(config, value)
    with pytest.raises(LifecycleError, match="connection_migration_required"):
        run(config)
    diagnostic = json.loads((controller.c.cloud_root / "startup-diagnostic.json").read_text())
    assert diagnostic["reason"] == "connection_migration_required"
    assert count(world, controller.c.alias) == 0


@pytest.mark.skipif(os.name != "nt", reason="official Windows FILETIME identity contract")
def test_vendor_creation_identity_allows_slow_registration_and_rejects_pid_reuse(world):
    controller, _ = setup(world)
    controller.ensure_ready()
    daemons, children = controller.scan()
    observed = controller.probe()
    meta = observed["process"]
    meta["started_at"] = "2099-01-01T00:00:00Z"
    meta["pid_start_time"] = str(round(daemons[0].created * 1_000_000_000))
    meta["pid_executable"] = daemons[0].exe
    assert controller.verified_ready(observed, daemons, children)
    meta["pid_start_time"] = str(round((daemons[0].created - 10) * 1_000_000_000))
    with pytest.raises(OwnershipError, match="runtime_start_identity_conflict"):
        controller.verified_ready(observed, daemons, children)


def test_confirmed_daemon_exit_recovers_without_waiting_readiness_deadline(world, monkeypatch):
    from origin_agent.tunnel_lifecycle import StopRequested

    controller, _ = setup(world)
    controller.policy = replace(controller.policy, ready_timeout=60, retries=(0.01,))
    original_note = controller.note
    ready_count = 0

    def note(state, **kwargs):
        nonlocal ready_count
        value = original_note(state, **kwargs)
        if state == "ready":
            ready_count += 1
            if ready_count == 1:
                controller.terminate(kwargs["daemon"])
            elif ready_count == 2:
                raise StopRequested("stop_requested")
        return value

    monkeypatch.setattr(controller, "note", note)
    began = time.monotonic()
    assert controller.supervise()["state"] == "stopped"
    assert time.monotonic() - began < 12
    assert count(world, controller.c.alias) == 2


@pytest.mark.skipif(os.name != "nt", reason="pinned Windows client identity contract")
def test_migrated_connection_requires_vendor_os_identity(world):
    controller, _ = setup(world)
    controller.ensure_ready()
    daemons, children = controller.scan()
    observed = controller.probe()
    observed["process"].pop("pid_start_time")
    with pytest.raises(LifecycleError, match="runtime_start_identity_missing"):
        controller.verified_ready(observed, daemons, children)


@pytest.mark.skipif(os.name != "nt", reason="Windows vendor identity projection")
def test_status_uses_scoped_persisted_identity_when_cli_projection_omits_it(world):
    controller, _ = setup(world)
    controller.ensure_ready()
    observed = controller.probe()
    record = dict(observed["process"], alias=controller.c.alias)
    write_json(controller.c.client_state_dir / "processes.yaml", {controller.c.alias: record})
    observed["process"].pop("pid_start_time")
    observed["process"].pop("pid_executable")
    write_json(
        world / controller.c.alias / "settings.json", {"status_override": {"stdout": json.dumps(observed)}}
    )
    merged = controller.probe()
    assert controller.verified_ready(merged, *controller.scan())
    record["pid"] += 1
    write_json(controller.c.client_state_dir / "processes.yaml", {controller.c.alias: record})
    with pytest.raises(OwnershipError, match="runtime_registry_identity_conflict"):
        controller.probe()


def test_remote_auth_failure_stops_owned_chain_and_blocks_unchanged_credential(world):
    controller, config = setup(world)
    daemon = controller.ensure_ready()
    controller.remote_probe = lambda *_: {
        "state": "authentication_required",
        "reason": "authentication_required",
    }
    result = controller.supervise()
    assert result["state"] == "blocked" and not result["ready"]
    assert result["recovery_action"] == "update_connection_credential"
    assert not daemon.live() and controller.scan() == ([], [])
    assert controller.authentication_blocked()
    before = count(world, controller.c.alias)
    assert controller.supervise()["state"] == "blocked"
    assert count(world, controller.c.alias) == before
    controller.c.secret_file.write_bytes(b"encrypted-fixture-revision-two")
    assert not controller.authentication_blocked()
    # Updating credentials does not override an explicit user stop.
    write_json(controller.c.cloud_root / "intent.json", {"enabled": False, "stop_requested": True})
    assert controller.supervise()["state"] == "stopped"
    assert count(world, controller.c.alias) == before


def test_remote_outage_keeps_owner_and_never_claims_ready(world):
    controller, config = setup(world)
    daemon = controller.ensure_ready()
    before = count(world, controller.c.alias)
    for state in ("recovering", "unknown", "recovering", "online"):
        controller.remote_probe = lambda *_, state=state: {"state": state, "reason": None, "idle": True}
        result = controller.observe_connection(daemon)
        assert result["ready"] is (state == "online")
        assert result["local_mcp_ready"]
        assert daemon.live() and count(world, controller.c.alias) == before
    assert status(config)["remote_reachability"] == "online"


def test_resume_grace_preserves_owner_then_idle_stall_can_be_reconciled(world, monkeypatch):
    import origin_agent.tunnel_lifecycle as module

    controller, _ = setup(world)
    daemon = controller.ensure_ready()
    tick = [1000.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: tick[0])
    controller.last_health_tick = 500
    controller.remote_grace_until = 0
    controller.policy = replace(controller.policy, resume_grace=10, stall_grace=2)
    controller.remote_probe = lambda *_: {"state": "stalled", "reason": "control_plane_stalled", "idle": True}
    assert controller.observe_connection(daemon)["state"] == "degraded"
    tick[0] += 3
    assert controller.observe_connection(daemon)["state"] == "degraded"
    tick[0] += 8
    with pytest.raises(LifecycleError, match="control_plane_stalled"):
        controller.observe_connection(daemon)
    assert daemon.live()  # The observation itself never terminates a process.
    controller.remote_probe = lambda *_: {
        "state": "stalled",
        "reason": "control_plane_stalled",
        "idle": False,
    }
    assert controller.observe_connection(daemon)["state"] == "degraded"


def test_auth_failure_does_not_block_a_credential_updated_during_the_attempt(world):
    controller, _ = setup(world)
    original = controller.credential_revision()

    def rejected_old_credential(*_):
        controller.c.secret_file.write_bytes(b"updated-while-old-key-is-loaded")
        return {"state": "authentication_required", "reason": "authentication_required"}

    controller.remote_probe = rejected_old_credential
    assert controller.supervise()["state"] == "blocked"
    block = json.loads((controller.c.cloud_root / "authentication-blocked.json").read_text())
    assert block["credential_revision"] == original
    assert not controller.authentication_blocked()


def test_confirmed_idle_stall_replaces_only_its_owner_and_stop_still_wins(world):
    controller, _ = setup(world, name="stall-owner")
    other, _ = setup(world, name="other-account")
    first = controller.ensure_ready()
    untouched = other.ensure_ready()
    controller.policy = replace(controller.policy, resume_grace=0, stall_grace=0, retries=(0,))
    controller.remote_grace_until = 0
    replacements = []

    def remote_health(_connection, daemon):
        if daemon.pid == first.pid and daemon.created == first.created:
            return {"state": "stalled", "reason": "control_plane_stalled", "idle": True}
        replacements.append(daemon)
        assert not first.live()
        assert untouched.live() and count(world, other.c.alias) == 1
        assert count(world, controller.c.alias) == 2
        write_json(controller.c.cloud_root / "intent.json", {"enabled": False, "stop_requested": True})
        return {"state": "online", "reason": None, "idle": True}

    controller.remote_probe = remote_health
    assert controller.supervise()["state"] == "stopped"
    assert len(replacements) == 1 and not replacements[0].live()
    assert untouched.live() and controller.scan() == ([], [])


def test_local_probe_failure_invalidates_previous_remote_success(world):
    controller, config = setup(world)
    daemon = controller.ensure_ready()
    assert controller.observe_connection(daemon)["remote_reachability"] == "online"
    controller.note("degraded", reason="command_timeout", daemon=daemon)
    observed = status(config)
    assert not observed["ready"]
    assert observed["remote_reachability"] == "unknown"
    assert daemon.live()
