import json

import pytest
from test_stdio_binding import package  # noqa: F401

from origin_agent.stdio_binding import create_binding, digest
from origin_agent.stdio_migration import replace_configuration, stage_configuration


@pytest.mark.parametrize("suffix", [".json", ".toml"])
def test_staging_and_exact_rollback_preserve_other_servers(package, tmp_path, monkeypatch, suffix):  # noqa: F811
    monkeypatch.setenv("ORIGIN_AGENT_HOME", str(tmp_path / "isolated"))
    executable = package[1]
    binding = tmp_path / "binding.json"
    create_binding(executable, ["serve", "--profile", "economy"], binding)
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    bridge = adapter / "origin-stdio-bridge.exe"
    bridge.write_bytes(b"synthetic; never execute")
    (adapter / "build-inventory.json").write_text(
        json.dumps({"adapter_version": "0.1.0", "engine_included": False})
    )
    (adapter / "checksums.json").write_text(json.dumps({p.name: digest(p) for p in adapter.iterdir()}))
    config, candidate = tmp_path / ("host" + suffix), tmp_path / ("proposed" + suffix)
    old_command, old_args = json.dumps(str(executable)), json.dumps(["serve", "--profile", "economy"])
    new_command, new_args = json.dumps(str(bridge)), json.dumps(["serve", "--binding", str(binding)])
    if suffix == ".toml":
        before = f"# preserved comment\n[mcp_servers.origin]\ncommand = {old_command}\nargs = {old_args}\n"
        before += (
            '[mcp_servers.origin.env]\nTEST_VALUE = "unchanged"\n[mcp_servers.other]\ncommand = "other"\n'
        )
    else:
        before = json.dumps(
            {
                "mcpServers": {
                    "origin": {
                        "command": str(executable),
                        "args": ["serve", "--profile", "economy"],
                        "env": {"TEST_VALUE": "unchanged"},
                        "cwd": str(tmp_path),
                    },
                    "other": {"command": "other"},
                },
                "other_setting": 9,
            }
        )
    after = before.replace(old_command, new_command).replace(old_args, new_args)
    config.write_bytes(before.encode())
    candidate.write_bytes(after.encode())
    receipt = tmp_path / "private-receipt"
    stage_configuration(config, candidate, binding, bridge, "origin", receipt)
    assert config.read_bytes() == before.encode()
    with pytest.raises(ValueError, match="checkpoint"):
        replace_configuration(receipt)
    extra = adapter / "unexpected.dll"
    extra.write_bytes(b"package drift")
    with pytest.raises(ValueError, match="file set changed"):
        replace_configuration(receipt, checkpoint=True)
    extra.unlink()
    replace_configuration(receipt, checkpoint=True)
    assert config.read_bytes() == after.encode()
    replace_configuration(receipt, rollback=True, checkpoint=True)
    assert config.read_bytes() == before.encode()
    replace_configuration(receipt, checkpoint=True)
    config.write_bytes(after.encode() + b"\n")
    with pytest.raises(ValueError, match="changed"):
        replace_configuration(receipt, rollback=True, checkpoint=True)
    assert config.read_bytes() == after.encode() + b"\n"
    candidate.write_text(after.replace("unchanged", "modified"))
    config.write_bytes(before.encode())
    with pytest.raises(ValueError, match="Only the selected"):
        stage_configuration(config, candidate, binding, bridge, "origin", tmp_path / "invalid")
