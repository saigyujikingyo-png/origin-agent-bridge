import hashlib
import json
import subprocess
import sys
from contextlib import contextmanager

import pytest

from origin_agent import tunnel_lifecycle
from origin_agent.installation import Changes
from origin_agent.lifecycle_admission import (
    AdmissionError,
    admitted,
    intent_guard,
    pending_transaction,
    transaction,
)
from origin_agent.storage import BusyError, file_lock, write_json
from origin_agent.tunnel_lifecycle import (
    Connection,
    Controller,
    LifecycleError,
    allow_start,
    run,
    status,
    stop,
)


@pytest.fixture
def scope(tmp_path):
    state = tmp_path / "state"
    cloud = state / "cloud"
    config = cloud / "runtime-config.json"
    write_json(state / "install.json", {"version": "fixture", "executable": sys.executable})
    write_json(
        config,
        {
            "schema_version": 1,
            "alias": "test-admission",
            "profile": "test-admission",
            "state_root": str(state),
            "cloud_root": str(cloud),
            "profile_dir": str(cloud / "profiles"),
            "secret_file": str(cloud / "secret.dpapi"),
            "tunnel_client": sys.executable,
        },
    )
    write_json(cloud / "intent.json", {"enabled": False, "stop_requested": True})
    return state, config


def complete(changes, value):
    changes.value["status"] = value
    changes.save()


def test_transaction_blocks_supported_start_without_holding_runtime_lock(scope):
    state, config = scope
    connection = Connection.load(config)
    before = (connection.cloud_root / "intent.json").read_bytes()
    changes = Changes(state)
    with transaction(state, changes.root.name):
        # Taking the runtime lock proves this is a different admission fence;
        # stop remains able to acquire the runtime lock without a deadlock.
        with file_lock(connection.lock, timeout=0):
            for action in (allow_start, run):
                with pytest.raises(AdmissionError, match="transaction_busy"):
                    action(config)
        assert (connection.cloud_root / "intent.json").read_bytes() == before
        assert status(config)["state"] == "maintenance"
        assert status(config)["receipt_id"] == changes.root.name
        complete(changes, "installed")
    assert pending_transaction(state) is None


def test_failed_rollback_keeps_fence_when_receipt_still_says_installed(scope):
    state, _ = scope
    changes = Changes(state)
    complete(changes, "installed")
    with pytest.raises(RuntimeError, match="restore refused"):
        with transaction(state, changes.root.name, recovery=True):
            raise RuntimeError("restore refused")
    assert pending_transaction(state)["receipt_id"] == changes.root.name
    with pytest.raises(AdmissionError, match="recovery_required"):
        with admitted(state):
            pytest.fail("partially rolled-back state was admitted")
    with transaction(state, changes.root.name, recovery=True):
        complete(changes, "rolled_back")
    assert pending_transaction(state) is None


def test_nested_successful_rollback_clears_fence_and_keeps_original_error(scope):
    state, _ = scope
    changes = Changes(state)
    with pytest.raises(ValueError, match="original failure"):
        with transaction(state, changes.root.name):
            try:
                raise ValueError("original failure")
            except ValueError:
                with transaction(state, changes.root.name, recovery=True):
                    complete(changes, "rolled_back")
                raise
    assert pending_transaction(state) is None


def test_cross_process_crash_requires_matching_explicit_recovery(scope):
    state, config = scope
    changes = Changes(state)
    code = """
import os, sys
from pathlib import Path
from origin_agent.lifecycle_admission import transaction
with transaction(Path(sys.argv[1]), sys.argv[2]):
    os._exit(19)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(state), changes.root.name],
        capture_output=True,
        timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode == 19
    assert pending_transaction(state)["receipt_id"] == changes.root.name
    for action in (allow_start, run):
        with pytest.raises(AdmissionError, match="recovery_required"):
            action(config)
    different = Changes(state)
    for recovery in (False, True):
        with pytest.raises(AdmissionError, match="recovery_required"):
            with transaction(state, different.root.name, recovery=recovery):
                pytest.fail("wrong recovery receipt was admitted")
    with transaction(state, changes.root.name, recovery=True):
        complete(changes, "rolled_back")
    allow_start(config)
    assert not Connection.load(config).intent()["stop_requested"]


def test_second_installer_is_blocked_in_another_process(scope):
    state, _ = scope
    first, second = Changes(state), Changes(state)
    code = """
import sys
from pathlib import Path
from origin_agent.lifecycle_admission import AdmissionError, transaction
try:
    with transaction(Path(sys.argv[1]), sys.argv[2]):
        raise AssertionError('competing transaction admitted')
except AdmissionError as exc:
    assert str(exc) == 'lifecycle_transaction_busy'
    print('blocked')
"""
    with transaction(state, first.root.name):
        result = subprocess.run(
            [sys.executable, "-c", code, str(state), second.root.name],
            capture_output=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        assert result.returncode == 0 and result.stdout.strip() == b"blocked", result.stderr
        complete(first, "installed")


def test_runtime_releases_admission_after_acquiring_scope(scope, monkeypatch):
    state, config = scope
    allow_start(config)

    def supervised(controller):
        with pytest.raises(BusyError):
            with file_lock(controller.c.lock, timeout=0):
                pytest.fail("runtime scope is unlocked")
        # An install may now enter admission and request cooperative stop;
        # the supervisor does not hold admission while waiting for stop.
        with admitted(state):
            return {"state": "fixture_running"}

    monkeypatch.setattr(Controller, "supervise", supervised)
    assert run(config)["state"] == "fixture_running"


def test_runtime_rejects_executable_selected_before_pointer_switch(scope, monkeypatch):
    state, config = scope
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    current = json.loads((state / "install.json").read_text())
    current["executable"] = str(state / "new-engine.exe")
    write_json(state / "install.json", current)
    with pytest.raises(LifecycleError, match="engine_changed_restart_required"):
        run(config)


def test_invalid_fence_never_admits_or_claims_ready(scope):
    state, config = scope
    marker = state / "cloud/lifecycle-transaction.json"
    marker.write_text("{broken")
    with pytest.raises(AdmissionError, match="invalid_recovery_required"):
        allow_start(config)
    assert status(config)["state"] == "unknown" and not status(config)["ready"]


def test_intent_guard_is_separate_from_runtime_scope(scope):
    _, config = scope
    connection = Connection.load(config)
    with file_lock(connection.lock, timeout=0):
        with intent_guard(connection.cloud_root):
            path = connection.cloud_root / ".lifecycle-intent.lock"
            with pytest.raises(BusyError):
                with file_lock(path, timeout=0):
                    pytest.fail("intent compare/write region is not protected")


@pytest.mark.parametrize("fail_cleanup", [False, True])
def test_stop_receipt_does_not_absorb_a_later_manual_stop(scope, monkeypatch, fail_cleanup):
    _, config = scope
    allow_start(config)
    original = {}

    def manual_stop_after_quiesce(controller):
        intent = controller.c.cloud_root / "intent.json"
        original["sha256"] = hashlib.sha256(intent.read_bytes()).hexdigest()
        with intent_guard(controller.c.cloud_root):
            write_json(intent, {"enabled": False, "stop_requested": True, "updated_at": "later user stop"})
        if fail_cleanup:
            raise LifecycleError("cleanup_refused")

    monkeypatch.setattr(Controller, "reconcile", manual_stop_after_quiesce)
    if fail_cleanup:
        with pytest.raises(LifecycleError, match="cleanup_refused") as raised:
            stop(config, disable=False)
        digest = raised.value.intent_sha256
    else:
        digest = stop(config, disable=False)["intent_sha256"]
    current = (Connection.load(config).cloud_root / "intent.json").read_bytes()
    assert digest == original["sha256"] != hashlib.sha256(current).hexdigest()
    assert json.loads(current)["enabled"] is False


def test_stop_precondition_preserves_manual_stop_after_installer_snapshot(scope):
    _, config = scope
    allow_start(config)
    intent = Connection.load(config).cloud_root / "intent.json"
    expected = hashlib.sha256(intent.read_bytes()).hexdigest()
    write_json(intent, {"enabled": False, "stop_requested": True, "updated_at": "manual stop"})
    stopped = intent.read_bytes()
    with pytest.raises(LifecycleError, match="intent_changed_before_stop"):
        stop(config, disable=False, expected_intent_sha256=expected)
    assert intent.read_bytes() == stopped


@pytest.mark.parametrize("action", [allow_start, run])
def test_config_rebind_cannot_enter_another_fenced_state_root(scope, monkeypatch, action):
    state, config = scope
    second = state.parent / "second-state"
    cloud = second / "cloud"
    write_json(cloud / "intent.json", {"enabled": False, "stop_requested": True})
    before = (cloud / "intent.json").read_bytes()
    rebound = json.loads(config.read_text())
    rebound.update(state_root=str(second), cloud_root=str(cloud), profile_dir=str(cloud / "profiles"))
    original_admitted = admitted

    @contextmanager
    def rebind_after_lock(root):
        with original_admitted(root):
            write_json(config, rebound)
            yield

    changes = Changes(second)
    with transaction(second, changes.root.name):
        monkeypatch.setattr(tunnel_lifecycle, "admitted", rebind_after_lock)
        with pytest.raises(LifecycleError, match="connection_scope_changed"):
            action(config)
        assert (cloud / "intent.json").read_bytes() == before
        complete(changes, "installed")


def test_stop_journal_failure_prevents_intent_write(scope):
    _, config = scope
    intent = Connection.load(config).cloud_root / "intent.json"
    before = intent.read_bytes()

    def refuse_journal(_digest):
        raise OSError("journal write refused")

    with pytest.raises(OSError, match="journal write refused"):
        stop(config, before_intent_write=refuse_journal)
    assert intent.read_bytes() == before


def test_stop_write_is_journaled_before_abrupt_process_death(scope):
    state, config = scope
    changes = Changes(state)
    journal = changes.root / "stop-write.json"
    code = """
import os, sys
from pathlib import Path
from origin_agent.lifecycle_admission import transaction
from origin_agent.storage import write_json
from origin_agent.tunnel_lifecycle import Controller, stop
Controller.reconcile = lambda self: os._exit(19)
def prepared(digest):
    write_json(Path(sys.argv[4]), {'intent_sha256':digest})
with transaction(Path(sys.argv[1]),sys.argv[2]):
    stop(Path(sys.argv[3]),disable=False,before_intent_write=prepared)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(state), changes.root.name, str(config), str(journal)],
        capture_output=True,
        timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode == 19, result.stderr
    written = (Connection.load(config).cloud_root / "intent.json").read_bytes()
    assert json.loads(journal.read_text())["intent_sha256"] == hashlib.sha256(written).hexdigest()
    assert pending_transaction(state)["receipt_id"] == changes.root.name


def test_manual_run_permission_preserves_disabled_startup_preference(scope):
    _, config = scope
    intent = Connection.load(config).cloud_root / "intent.json"
    write_json(intent, {"enabled": False, "stop_requested": True, "startup_enabled": False})
    allow_start(config)
    current = json.loads(intent.read_text())
    assert current["enabled"] is True and current["stop_requested"] is False
    assert current["startup_enabled"] is False


def test_wrong_recovery_receipt_cannot_deadlock_pending_activation(scope):
    state, _ = scope
    pending, wrong = Changes(state), Changes(state)
    complete(pending, "rolled_back")
    complete(wrong, "installed")
    write_json(state / "cloud/rollback-activation.json", {"receipt_id": pending.root.name})
    for recovery in (False, True):
        with pytest.raises(AdmissionError, match="rollback activation pending"):
            with transaction(state, wrong.root.name, recovery=recovery):
                pytest.fail("wrong receipt wrote a blocking fence")
        assert pending_transaction(state) is None
    with transaction(state, pending.root.name, recovery=True):
        assert pending_transaction(state)["receipt_id"] == pending.root.name
    assert pending_transaction(state) is None
