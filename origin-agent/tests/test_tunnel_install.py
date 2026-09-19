import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from origin_agent import __version__, tunnel_install
from origin_agent.installation import Changes, integrate, rollback


class Tasks:
    """Task Scheduler boundary; all lifecycle files use the real filesystem."""

    user_sid = "S-1-5-21-fixture"
    powershell = "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"

    def __init__(self):
        self.tasks = {}
        self.starts = []
        self.fail_register = False

    def list(self):
        return list(self.tasks.values())

    def read(self, name, path="\\"):
        return self.tasks.get((path, name))

    def register(self, record):
        if self.fail_register:
            self.fail_register = False
            raise RuntimeError("registration failure")
        self.tasks[(record["path"], record["name"])] = dict(record)

    def disable(self, name, path="\\"):
        record = dict(self.tasks[(path, name)])
        record["enabled"] = False
        record["xml"] = tunnel_install.task_xml(record)
        self.tasks[(path, name)] = record

    def restore(self, name, path, xml):
        if xml is None:
            self.tasks.pop((path, name), None)
        else:
            record = tunnel_install.record_from_xml(name, path, xml)
            self.tasks[(path, name)] = record

    def start(self, name, path="\\"):
        self.starts.append((path, name))


class Lifecycle:
    def __init__(self):
        self.stopped = []
        self.fail = False

    def stop(self, config_path, disable=False):
        assert disable is False
        config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.stopped.append(config["alias"])
        intent = Path(config["cloud_root"]) / "intent.json"
        before = json.loads(intent.read_text()) if intent.exists() else {"enabled": True}
        intent.write_text(json.dumps({**before, "stop_requested": True}))
        if self.fail:
            raise RuntimeError("unresolved owner")
        return {"state": "stopped"}

    def allow_start(self, config_path):
        config = json.loads(Path(config_path).read_text())
        (Path(config["cloud_root"]) / "intent.json").write_text(
            json.dumps({"enabled": True, "stop_requested": False})
        )


@pytest.fixture
def setup(tmp_path, monkeypatch):
    bundle, state = tmp_path / "release", tmp_path / "用户 profile" / ".origin-agent"
    (bundle / "server").mkdir(parents=True)
    (bundle / "server/origin-agent.exe").write_bytes(b"new engine")
    (bundle / "manifest.json").write_text(json.dumps({"version": __version__}))
    for name in ("Run-ChatGPT-Tunnel.ps1", "Stop-ChatGPT-Tunnel.ps1"):
        (bundle / name).write_text("# release-owned " + name)
    state.mkdir(parents=True)
    old = {"version": "0.2.11", "root": str(tmp_path / "old"), "executable": str(tmp_path / "old.exe")}
    (tmp_path / "old.exe").write_bytes(b"old engine")
    (state / "install.json").write_text(json.dumps(old))
    client = state / "tunnel-client/v0.0.14/tunnel-client.exe"
    client.parent.mkdir(parents=True)
    client.write_bytes(b"official client")
    tasks, lifecycle = Tasks(), Lifecycle()
    monkeypatch.setattr(tunnel_install, "WindowsTasks", lambda: tasks)
    monkeypatch.setattr(tunnel_install, "lifecycle_api", lambda: lifecycle)
    return bundle, state, tasks, lifecycle


def profile(state, tasks, alias="origin-agent", account=None, enabled=True):
    cloud = state / "cloud"
    if account:
        cloud /= "accounts/" + account
    directory = cloud / "profiles"
    directory.mkdir(parents=True)
    data = {
        "control_plane": {
            "tunnel_id": "tunnel_" + ("b" if account else "a") * 32,
            "api_key": "env:CONTROL_PLANE_API_KEY",
        }
    }
    (directory / (alias + ".yaml")).write_text(json.dumps(data))
    secret = cloud / "runtime-key.dpapi" if account else state / "secrets/tunnel-key.dpapi"
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_bytes(b"encrypted fixture - never rewrite")
    (cloud / "Run-ChatGPT-Tunnel.ps1").write_bytes(b"# old account launcher")
    record = tunnel_install.new_task(alias, cloud, state, tasks, enabled=enabled)
    record["name"] = "Legacy " + alias
    record["xml"] = tunnel_install.task_xml(record)
    tasks.register(record)
    return cloud, secret, record


def test_upgrade_migrates_both_accounts_and_rollback_preserves_identity(setup):
    bundle, state, tasks, lifecycle = setup
    personal, personal_secret, first = profile(state, tasks)
    school, school_secret, second = profile(state, tasks, "origin-agent-school", "account-fixture")
    before_tasks = dict(tasks.tasks)
    before_pointer = (state / "install.json").read_bytes()
    before_profiles = {p: p.read_bytes() for p in state.rglob("*.yaml")}
    result = integrate(bundle, state, [])
    assert lifecycle.stopped == ["origin-agent", "origin-agent-school"]
    assert tasks.starts == []
    for cloud, secret, record in ((personal, personal_secret, first), (school, school_secret, second)):
        config = json.loads((cloud / "runtime-config.json").read_text())
        assert config["secret_file"] == str(secret.resolve())
        assert config["task_name"] == record["name"]
        assert config["profile_dir"] == str((cloud / "profiles").resolve())
        assert (cloud / "Run-ChatGPT-Tunnel.ps1").read_bytes() == (
            bundle / "Run-ChatGPT-Tunnel.ps1"
        ).read_bytes()
        assert not (cloud / "intent.json").exists()
        assert secret.read_bytes() == b"encrypted fixture - never rewrite"
    assert all(path.read_bytes() == data for path, data in before_profiles.items())
    rollback(state, result["receipt_id"])
    assert (state / "install.json").read_bytes() == before_pointer
    assert tasks.tasks == before_tasks
    assert not (school / "runtime-config.json").exists()
    assert (school / "Run-ChatGPT-Tunnel.ps1").read_bytes() == b"# old account launcher"


def test_disabled_and_manual_stop_survive_repeat_install(setup):
    bundle, state, tasks, lifecycle = setup
    cloud, _, task = profile(state, tasks, enabled=False)
    intent = b'{"enabled": false, "stop_requested": true}\n'
    (cloud / "intent.json").write_bytes(intent)
    integrate(bundle, state, [])
    integrate(bundle, state, [])
    assert tasks.read(task["name"])["enabled"] is False
    assert (cloud / "intent.json").read_bytes() == intent
    assert tasks.starts == []
    assert lifecycle.stopped == ["origin-agent", "origin-agent"]


def test_quiesce_failure_preserves_pointer_launchers_and_task_preference(setup):
    bundle, state, tasks, lifecycle = setup
    cloud, _, task = profile(state, tasks)
    before = (state / "install.json").read_bytes()
    lifecycle.fail = True
    with pytest.raises(RuntimeError, match="unresolved owner"):
        integrate(bundle, state, [])
    assert (state / "install.json").read_bytes() == before
    assert (cloud / "Run-ChatGPT-Tunnel.ps1").read_bytes() == b"# old account launcher"
    assert tasks.read(task["name"])["enabled"] is True
    assert not (cloud / "runtime-config.json").exists()


def test_register_failure_rolls_back_all_accounts(setup):
    bundle, state, tasks, _ = setup
    first, _, _ = profile(state, tasks)
    second, _, _ = profile(state, tasks, "second", "other")
    before = dict(tasks.tasks)
    tasks.fail_register = True
    with pytest.raises(RuntimeError, match="registration failure"):
        integrate(bundle, state, [])
    assert tasks.tasks == before
    for cloud in (first, second):
        assert not (cloud / "runtime-config.json").exists()
        assert not (cloud / "intent.json").exists()
        assert (cloud / "Run-ChatGPT-Tunnel.ps1").read_bytes() == b"# old account launcher"


def test_ambiguous_task_fails_before_quiesce_or_write(setup):
    bundle, state, tasks, lifecycle = setup
    cloud, _, task = profile(state, tasks)
    duplicate = dict(task, name="Another matching task")
    tasks.register(duplicate)
    before = (state / "install.json").read_bytes()
    with pytest.raises(RuntimeError, match="Ambiguous"):
        integrate(bundle, state, [])
    assert lifecycle.stopped == []
    assert tasks.starts == []
    assert (state / "install.json").read_bytes() == before
    assert not (cloud / "runtime-config.json").exists()


def test_rollback_refuses_changed_task_before_restoring_files(setup):
    bundle, state, tasks, _ = setup
    cloud, _, task = profile(state, tasks)
    result = integrate(bundle, state, [])
    installed_pointer = (state / "install.json").read_bytes()
    changed = dict(tasks.read(task["name"]), user_sid="someone-else")
    changed["xml"] = tunnel_install.task_xml(changed)
    tasks.register(changed)
    with pytest.raises(RuntimeError, match="Rollback conflict"):
        rollback(state, result["receipt_id"])
    assert (state / "install.json").read_bytes() == installed_pointer
    assert (cloud / "runtime-config.json").exists()


def test_multiple_profiles_in_one_root_refuse_ambiguous_scope(setup):
    bundle, state, tasks, lifecycle = setup
    cloud, _, _ = profile(state, tasks)
    (cloud / "profiles/extra.yaml").write_text((cloud / "profiles/origin-agent.yaml").read_text())
    with pytest.raises(ValueError, match="one managed profile"):
        integrate(bundle, state, [])
    assert lifecycle.stopped == []


def test_stop_intent_and_disabled_tasks_hold_until_pointer_commits(setup, monkeypatch):
    bundle, state, tasks, _ = setup
    cloud, _, task = profile(state, tasks)
    before = (state / "install.json").read_bytes()
    original_put = Changes.put

    def inspect_commit(self, path, data):
        if path == state / "install.json":
            assert (state / "install.json").read_bytes() == before
            assert tasks.read(task["name"])["enabled"] is False
            assert json.loads((cloud / "intent.json").read_text())["stop_requested"] is True
        return original_put(self, path, data)

    monkeypatch.setattr(Changes, "put", inspect_commit)
    integrate(bundle, state, [])
    assert tasks.read(task["name"])["enabled"] is True
    assert not (cloud / "intent.json").exists()


def test_unconfigured_profiles_do_not_gain_enabled_startup_on_upgrade(setup):
    bundle, state, tasks, _ = setup
    cloud, _, task = profile(state, tasks)
    tasks.tasks.pop((task["path"], task["name"]))
    result = integrate(bundle, state, [])
    assert result["private_tunnels"][0]["startup_enabled"] is False
    config = json.loads((cloud / "runtime-config.json").read_text())
    assert tasks.read(config["task_name"])["enabled"] is False
    assert tasks.starts == []
    rollback(state, result["receipt_id"])
    assert tasks.tasks == {}


@pytest.mark.parametrize("mutation", ["principal", "executable"])
def test_unproven_startup_task_preserved(setup, mutation):
    bundle, state, tasks, lifecycle = setup
    _, _, task = profile(state, tasks)
    if mutation == "principal":
        task["user_sid"] = "S-1-5-21-other-user"
    else:
        task["actions"] = [{**task["actions"][0], "execute": "C:/unrelated/powershell.exe"}]
    task["xml"] = tunnel_install.task_xml(task)
    tasks.register(task)
    before = dict(tasks.tasks)
    with pytest.raises(RuntimeError, match="ownership is unproven"):
        integrate(bundle, state, [])
    assert tasks.tasks == before
    assert lifecycle.stopped == []


def test_explicit_start_resumes_disabled_profile_only_after_migration(setup):
    bundle, state, tasks, _ = setup
    cloud, _, task = profile(state, tasks, enabled=False)
    (state / "install.json").write_text(json.dumps({"root": str(bundle), "version": __version__}))
    (cloud / "intent.json").write_text('{"enabled":false,"stop_requested":true}')
    result = tunnel_install.install_startup(state, start_now=True)
    assert result["profiles"][0]["started"] is True
    assert tasks.read(task["name"])["enabled"] is True
    assert tasks.starts == [("\\", task["name"])]
    assert json.loads((cloud / "intent.json").read_text()) == {"enabled": True, "stop_requested": False}


def test_startup_configuration_without_explicit_start_preserves_stop(setup):
    bundle, state, tasks, _ = setup
    cloud, _, task = profile(state, tasks, enabled=False)
    (state / "install.json").write_text(json.dumps({"root": str(bundle), "version": __version__}))
    original = b'{"enabled":false,"stop_requested":true}'
    (cloud / "intent.json").write_bytes(original)
    tunnel_install.install_startup(state)
    assert tasks.read(task["name"])["enabled"] is False
    assert tasks.starts == []
    assert (cloud / "intent.json").read_bytes() == original


def test_invalid_profile_does_not_rewrite_or_attempt_credential_recovery(setup):
    bundle, state, tasks, lifecycle = setup
    cloud, secret, _ = profile(state, tasks)
    source = cloud / "profiles/origin-agent.yaml"
    original = json.loads(source.read_text())
    original["control_plane"]["api_key"] = "literal-not-accepted"
    source.write_text(json.dumps(original))
    before = source.read_bytes()
    with pytest.raises(ValueError, match="environment key reference"):
        integrate(bundle, state, [])
    assert lifecycle.stopped == []
    assert source.read_bytes() == before
    assert secret.read_bytes() == b"encrypted fixture - never rewrite"


def test_receipt_never_copies_profile_identifier_or_key_data(setup):
    bundle, state, tasks, _ = setup
    cloud, secret, _ = profile(state, tasks)
    result = integrate(bundle, state, [])
    receipt_root = state / "installations" / result["receipt_id"]
    for file in receipt_root.iterdir():
        if file.is_file():
            content = file.read_bytes()
            assert b"tunnel_aaaaaaaa" not in content
            assert secret.read_bytes() not in content
    assert json.loads((cloud / "runtime-config.json").read_text())["schema_version"] == 1


def test_disabled_startup_adapter_only_disables_exact_scope(setup):
    bundle, state, tasks, _ = setup
    personal, _, first = profile(state, tasks)
    _, _, second = profile(state, tasks, "second", "second")
    integrate(bundle, state, [])
    result = tunnel_install.disable_startup(personal / "runtime-config.json")
    assert result == {"startup_enabled": False}
    assert tasks.read(first["name"])["enabled"] is False
    assert tasks.read(second["name"])["enabled"] is True


def test_completed_rollback_preserves_new_manual_stop_and_disabled_preference(setup):
    bundle, state, tasks, _ = setup
    cloud, _, task = profile(state, tasks)
    result = integrate(bundle, state, [])
    current = b'{"enabled":false,"stop_requested":true,"updated_at":"user-stop"}'
    (cloud / "intent.json").write_bytes(current)
    tasks.disable(task["name"])
    rollback(state, result["receipt_id"])
    assert (cloud / "intent.json").read_bytes() == current
    assert tasks.read(task["name"])["enabled"] is False
    assert (cloud / "Run-ChatGPT-Tunnel.ps1").read_bytes() == b"# old account launcher"


def test_partial_explicit_start_is_reconciled_before_rollback(setup, monkeypatch):
    bundle, state, tasks, lifecycle = setup
    first, _, _ = profile(state, tasks)
    second, _, _ = profile(state, tasks, "second", "second")
    (state / "install.json").write_text(json.dumps({"root": str(bundle), "version": __version__}))
    original_tasks = dict(tasks.tasks)
    original_start = tasks.start

    def fail_second(name, path="\\"):
        original_start(name, path)
        if len(tasks.starts) == 2:
            raise RuntimeError("start reported failure after a possible spawn")

    monkeypatch.setattr(tasks, "start", fail_second)
    with pytest.raises(RuntimeError, match="possible spawn"):
        tunnel_install.install_startup(state, start_now=True)
    assert lifecycle.stopped == ["origin-agent", "second", "origin-agent", "second"]
    assert tasks.tasks == original_tasks
    assert not (first / "intent.json").exists()
    assert not (second / "intent.json").exists()
    assert (first / "Run-ChatGPT-Tunnel.ps1").read_bytes() == b"# old account launcher"


def test_extra_task_action_referencing_scope_is_not_ignored(setup):
    bundle, state, tasks, lifecycle = setup
    _, _, task = profile(state, tasks)
    task["actions"] = task["actions"] + [{"execute": "cmd.exe", "arguments": "", "working_directory": ""}]
    task["xml"] = tunnel_install.task_xml(task)
    tasks.register(task)
    with pytest.raises(RuntimeError, match="ownership is unproven"):
        integrate(bundle, state, [])
    assert lifecycle.stopped == []


def test_published_upgrade_is_quiesced_again_on_pointer_failure(setup, monkeypatch):
    bundle, state, tasks, lifecycle = setup
    cloud, _, _ = profile(state, tasks)
    old = (state / "install.json").read_bytes()
    original_put = Changes.put

    def fail_pointer(self, path, data):
        if path == state / "install.json":
            raise OSError("pointer commit failed")
        return original_put(self, path, data)

    monkeypatch.setattr(Changes, "put", fail_pointer)
    with pytest.raises(OSError, match="pointer commit"):
        integrate(bundle, state, [])
    assert lifecycle.stopped == ["origin-agent", "origin-agent"]
    assert (state / "install.json").read_bytes() == old
    assert (cloud / "Run-ChatGPT-Tunnel.ps1").read_bytes() == b"# old account launcher"


def test_existing_task_action_via_directory_alias_is_reused(setup, tmp_path):
    bundle, state, tasks, _ = setup
    cloud, _, task = profile(state, tasks)
    alias = tmp_path / "cloud-alias"
    try:
        alias.symlink_to(cloud, target_is_directory=True)
    except OSError:
        pytest.skip("Creating directory links is not permitted on this Windows test account")
    task["actions"] = [{**task["actions"][0], "arguments": tunnel_install.launcher_arguments(alias)}]
    task["xml"] = tunnel_install.task_xml(task)
    tasks.register(task)
    integrate(bundle, state, [])
    assert len(tasks.tasks) == 1
    assert json.loads((cloud / "runtime-config.json").read_text())["task_name"] == task["name"]


def test_initialize_refuses_existing_identity_before_vendor_call(setup, monkeypatch):
    _, state, tasks, _ = setup
    cloud, _, _ = profile(state, tasks)
    before = (cloud / "profiles/origin-agent.yaml").read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("No vendor command may run for an existing profile")

    monkeypatch.setattr(tunnel_install.subprocess, "run", forbidden)
    with pytest.raises(RuntimeError, match="Existing private tunnel profile preserved"):
        tunnel_install.initialize_profile(
            state, "tunnel_abc", state / "tunnel-client/v0.0.14/tunnel-client.exe"
        )
    assert (cloud / "profiles/origin-agent.yaml").read_bytes() == before


def test_initialize_shares_canonical_runtime_lock(setup, monkeypatch):
    from origin_agent.storage import BusyError, file_lock

    _, state, _, _ = setup
    lock = state / "cloud/profiles/.origin-origin-agent.lock"
    with file_lock(lock, timeout=0), pytest.raises(BusyError):
        tunnel_install.initialize_profile(
            state, "tunnel_abc", state / "tunnel-client/v0.0.14/tunnel-client.exe"
        )
    assert not (state / "cloud/profiles/origin-agent.yaml").exists()


@pytest.mark.parametrize("conflict", [None, "concurrent_profile", "existing_task", "existing_owner"])
def test_initialize_publishes_only_new_valid_profile_under_ownership_guard(setup, monkeypatch, conflict):
    from origin_agent import tunnel_lifecycle

    _, state, tasks, _ = setup
    profile_path = state / "cloud/profiles/origin-agent.yaml"
    calls = []
    monkeypatch.setattr(
        tunnel_lifecycle.Controller,
        "scan",
        lambda self: ([object()], []) if conflict == "existing_owner" else ([], []),
    )
    if conflict == "existing_task":
        task = tunnel_install.new_task("origin-agent", state / "cloud", state, tasks, enabled=False)
        tasks.register(task)

    def vendor(argv, **kwargs):
        calls.append(argv)
        assert kwargs["timeout"] <= 30
        directory = Path(argv[argv.index("--profile-dir") + 1])
        assert directory != profile_path.parent
        (directory / "origin-agent.yaml").write_text(
            json.dumps({"control_plane": {"tunnel_id": "tunnel_abc", "api_key": "env:CONTROL_PLANE_API_KEY"}})
        )
        if conflict == "concurrent_profile":
            profile_path.write_bytes(b"concurrent owner profile")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(tunnel_install.subprocess, "run", vendor)
    if conflict == "concurrent_profile":
        with pytest.raises(FileExistsError):
            tunnel_install.initialize_profile(
                state, "tunnel_abc", state / "tunnel-client/v0.0.14/tunnel-client.exe"
            )
        assert profile_path.read_bytes() == b"concurrent owner profile"
    elif conflict:
        with pytest.raises(RuntimeError, match="already exists|registration preserved"):
            tunnel_install.initialize_profile(
                state, "tunnel_abc", state / "tunnel-client/v0.0.14/tunnel-client.exe"
            )
        assert calls == []
        assert not profile_path.exists()
    else:
        result = tunnel_install.initialize_profile(
            state, "tunnel_abc", state / "tunnel-client/v0.0.14/tunnel-client.exe"
        )
        assert result["state"] == "initialized"
        assert result["started"] is False
        assert json.loads(profile_path.read_text())["control_plane"]["api_key"] == "env:CONTROL_PLANE_API_KEY"
    assert tasks.starts == []


@pytest.mark.skipif(
    os.name != "nt", reason="DPAPI and the released Windows PowerShell adapter require Windows"
)
def test_real_powershell_wrapper_passes_scoped_home_and_key_without_argv_secret(tmp_path):
    state = tmp_path / "private account 状态"
    cloud = state / "cloud/accounts/fixture"
    cloud.mkdir(parents=True)
    captured = tmp_path / "captured.json"
    engine = tmp_path / "fixture-engine.ps1"
    engine.write_text(
        "[pscustomobject]@{arguments=@($args); state=$env:ORIGIN_AGENT_HOME; "
        "keyPresent=($env:CONTROL_PLANE_API_KEY -eq 'sk-dpapi-fixture')} | "
        "ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -LiteralPath $env:ORIGIN_TEST_CAPTURE\n"
        "$global:LASTEXITCODE = 0\n",
        encoding="utf-8-sig",
    )
    (state / "install.json").write_text(json.dumps({"executable": str(engine)}))
    secret = cloud / "runtime-key.dpapi"
    config = cloud / "runtime-config.json"
    config.write_text(json.dumps({"schema_version": 1, "state_root": str(state), "secret_file": str(secret)}))
    runner = Path(__file__).resolve().parents[1] / "scripts/Run-ChatGPT-Tunnel.ps1"
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    environment = {
        **os.environ,
        "ORIGIN_TEST_SECRET": str(secret),
        "ORIGIN_TEST_CONFIG": str(config),
        "ORIGIN_TEST_RUNNER": str(runner),
        "ORIGIN_TEST_CAPTURE": str(captured),
        "ORIGIN_AGENT_HOME": "original-home-fixture",
        "CONTROL_PLANE_API_KEY": "sk-original-fixture",
    }
    # Keep inherited module paths: the shipped adapter must tolerate Codex/PS7.
    harness = r"""
    $ErrorActionPreference = 'Stop'
    Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1')
    $sealed = ConvertTo-SecureString 'sk-dpapi-fixture' -AsPlainText -Force | ConvertFrom-SecureString
    [IO.File]::WriteAllText($env:ORIGIN_TEST_SECRET, $sealed)
    & $env:ORIGIN_TEST_RUNNER -ConfigPath $env:ORIGIN_TEST_CONFIG
    if ($LASTEXITCODE -ne 0) { throw 'Runner fixture failed.' }
    if ($env:ORIGIN_AGENT_HOME -ne 'original-home-fixture') { throw 'State environment was not restored.' }
    if ($env:CONTROL_PLANE_API_KEY -ne 'sk-original-fixture') {
        throw 'Credential environment was not restored.'
    }
    """
    result = subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", harness],
        env=environment,
        capture_output=True,
        timeout=20,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    value = json.loads(captured.read_text(encoding="utf-8-sig"))
    assert value["arguments"] == ["tunnel", "run", "--config", str(config)]
    assert value["state"] == str(state)
    assert value["keyPresent"] is True
    assert "sk-" not in json.dumps(value)
