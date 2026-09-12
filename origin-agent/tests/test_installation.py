import json
from pathlib import Path

import pytest

from origin_agent import __version__
from origin_agent.installation import Changes, integrate, rollback


def bundle(tmp_path):
    root = tmp_path / "release"
    (root / "server").mkdir(parents=True)
    (root / "server/origin-agent.exe").write_bytes(b"fixture")
    (root / "manifest.json").write_text(json.dumps({"version": __version__}))
    (root / "skills/origin-workflow").mkdir(parents=True)
    (root / "skills/origin-workflow/SKILL.md").write_text("fixture instructions")
    return root


def test_install_preserves_settings_and_rollback(tmp_path):
    source = bundle(tmp_path)
    home, state, appdata = tmp_path / "用户 profile", tmp_path / "state", tmp_path / "roaming"
    config = appdata / "Claude/claude_desktop_config.json"
    config.parent.mkdir(parents=True)
    original = b'{"mcpServers":{"unrelated":{"command":"keep"}},"preferences":{"theme":"dark"}}'
    config.write_bytes(original)
    result = integrate(source, state, ["claude", "workbuddy"], user_home=home, appdata=appdata)
    installed = json.loads(config.read_text(encoding="utf-8"))
    assert installed["preferences"] == {"theme": "dark"}
    assert installed["mcpServers"]["unrelated"]["command"] == "keep"
    assert Path(installed["mcpServers"]["origin-agent"]["command"]).is_absolute()
    assert (home / ".workbuddy/skills/origin-workflow/SKILL.md").is_file()
    rollback(state, result["receipt_id"])
    assert config.read_bytes() == original
    assert not (state / "install.json").exists()
    assert not (home / ".workbuddy/mcp.json").exists()
    assert rollback(state, result["receipt_id"])["status"] == "rolled_back"


def test_invalid_configuration_does_not_switch_install(tmp_path):
    source = bundle(tmp_path)
    appdata, state = tmp_path / "roaming", tmp_path / "state"
    config = appdata / "Claude/claude_desktop_config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{"mcpServers":[]}')
    with pytest.raises(ValueError, match="structure"):
        integrate(source, state, ["claude"], user_home=tmp_path / "profile", appdata=appdata)
    assert not (state / "install.json").exists()


def test_rollback_refuses_subsequent_user_edit(tmp_path):
    changes = Changes(tmp_path)
    first, second = tmp_path / "a", tmp_path / "b"
    first.write_bytes(b"old")
    changes.put(first, b"installed")
    changes.put(second, b"installed")
    second.write_bytes(b"user edit")
    with pytest.raises(RuntimeError, match="conflict"):
        rollback(tmp_path, changes.root.name)
    assert first.read_bytes() == b"installed"
    assert second.read_bytes() == b"user edit"


def test_partial_install_is_reversible(tmp_path, monkeypatch):
    source = bundle(tmp_path)
    original_put = Changes.put

    def fail_pointer(self, path, data):
        if path.name == "install.json":
            raise OSError("simulated interruption")
        original_put(self, path, data)

    monkeypatch.setattr(Changes, "put", fail_pointer)
    with pytest.raises(OSError, match="interruption"):
        integrate(source, tmp_path / "state", ["workbuddy"], user_home=tmp_path / "profile")
    assert not (tmp_path / "profile/.workbuddy/mcp.json").exists()
    assert not (tmp_path / "state/install.json").exists()


def test_openai_and_legacy_codex_selection_do_not_add_a_duplicate_mcp(tmp_path, monkeypatch):
    source = bundle(tmp_path)

    def forbidden(*args):
        raise AssertionError("OpenAI must reuse the connected app, not add a local Codex MCP")

    monkeypatch.setattr(Changes, "codex", forbidden)
    for host in ("openai", "codex"):
        home = tmp_path / host
        result = integrate(source, tmp_path / (host + "-state"), [host], user_home=home)
        assert result["hosts"] == ["openai"]
        assert not (home / ".codex/config.toml").exists()
        assert not (home / ".agents/skills").exists()
