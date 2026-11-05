import json
from pathlib import Path

import pytest

import origin_agent.stdio_binding as binding


@pytest.fixture
def package(tmp_path):
    root = tmp_path / "original"
    server = root / "server"
    server.mkdir(parents=True)
    executable = server / "origin-agent.exe"
    executable.write_bytes(b"synthetic package; never execute")
    supported = json.loads((Path(binding.__file__).parent / "data" / "stdio_backends.json").read_text())
    inventory = {
        "version": "0.2.8",
        "source_hashes": {key: hashes[0] for key, hashes in supported["0.2.8"]["source_hashes"].items()},
        "packages_in_build_environment": [{"name": "mcp", "version": "2.2.0"}],
    }
    (root / "build-inventory.json").write_text(json.dumps(inventory))
    files = {p.relative_to(root).as_posix(): binding.digest(p) for p in root.rglob("*") if p.is_file()}
    (root / "checksums.json").write_text(json.dumps(files))
    return root, executable


def test_binding_preserves_original_args_and_private_context(package, tmp_path, monkeypatch):
    root, executable = package
    runtime = tmp_path / "isolated state"
    runtime.mkdir()
    monkeypatch.setenv("ORIGIN_AGENT_HOME", str(runtime))
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "binding.json"
    args = ["serve", "--profile", "economy", "--vision=off", "--model-preset", "generic"]
    binding.create_binding(executable, args, target)
    loaded = binding.load_binding(target)
    loaded.verify()
    assert loaded.command == [str(executable), *args]
    assert loaded.root == runtime and loaded.cwd == tmp_path
    assert "environment" not in json.loads(target.read_text())
    monkeypatch.setenv("BRIDGE_TEST_CONTEXT", "changed")
    with pytest.raises(ValueError, match="context"):
        loaded.verify()


@pytest.mark.parametrize("change", ["runtime", "extra_file", "profile", "binding", "inventory"])
def test_wake_refuses_changed_identity(package, tmp_path, monkeypatch, change):
    root, executable = package
    monkeypatch.setenv("ORIGIN_AGENT_HOME", str(tmp_path))
    target = tmp_path / "binding.json"
    binding.create_binding(executable, ["serve"], target)
    loaded = binding.load_binding(target)
    loaded.verify()
    if change == "runtime":
        executable.write_bytes(b"replacement")
    elif change == "extra_file":
        (executable.parent / "untracked.dll").write_bytes(b"extra")
    elif change == "profile":
        (tmp_path / "agent-profile.json").write_text("{}")
    elif change == "binding":
        target.write_text(target.read_text() + " ")
    else:
        (root / "build-inventory.json").write_text("{}")
    with pytest.raises(ValueError):
        loaded.verify()


@pytest.mark.parametrize(
    "args",
    [
        ["supervise"],
        ["serve", "--transport", "streamable-http"],
        ["serve", "--profile", "economy", "--profile", "full"],
        ["serve", "--unknown", "x"],
    ],
)
def test_unsafe_or_ambiguous_launch_refused(package, tmp_path, args):
    with pytest.raises(ValueError):
        binding.create_binding(package[1], args, tmp_path / "binding.json")


def test_modified_source_or_protocol_dependency_refused(package, tmp_path):
    root, executable = package
    path = root / "build-inventory.json"
    inventory = json.loads(path.read_text())
    inventory["packages_in_build_environment"][0]["version"] = "different"
    path.write_text(json.dumps(inventory))
    with pytest.raises(ValueError, match="protocol dependency"):
        binding.create_binding(executable, ["serve"], tmp_path / "binding.json")


def test_no_binding_overwrite(package, tmp_path):
    path = tmp_path / "binding.json"
    binding.create_binding(package[1], ["serve"], path)
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        binding.create_binding(package[1], ["serve"], path)
    assert path.read_bytes() == before
