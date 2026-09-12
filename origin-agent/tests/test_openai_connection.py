import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp import Client

from origin_agent import openai_connection as oc
from origin_agent.installation import rollback
from origin_agent.server import make_server
from origin_agent.storage import Store

APP = "asdk_app_" + "a" * 32
URL = "https://chatgpt.com/plugins/plugin_" + APP


@pytest.mark.parametrize("value", [APP, "plugin_" + APP, URL, URL + "?view=personal#settings/Plugins/x"])
def test_normalises_only_registered_app_identifiers(value):
    assert oc.normalise_connection(value)["plugin_url"] == URL


@pytest.mark.parametrize(
    "value",
    [
        "https://chatgpt.com.evil.invalid/plugins/plugin_" + APP,
        "https://someone@chatgpt.com/plugins/plugin_" + APP,
        "http://chatgpt.com/plugins/plugin_" + APP,
        "https://chatgpt.com:443/plugins/plugin_" + APP,
        "https://chatgpt.com/c/" + APP,
        "sk-not-a-plugin-link",
        "../" + APP,
    ],
)
def test_rejects_keys_other_sites_and_conversation_links(value):
    with pytest.raises(ValueError):
        oc.normalise_connection(value)


def test_account_binding_is_reversible_and_does_not_claim_host_acceptance(tmp_path):
    state = tmp_path / "state"
    assert oc.connection_info(state)["configured"] is False
    result = oc.connect_openai(state, URL, user_home=tmp_path / "home")
    assert result["host_workflow_verified"] is False
    assert result["model_called"] is False
    assert oc.connection_info(state)["app_id"] == APP
    rollback(state, result["receipt_id"])
    assert oc.connection_info(state)["configured"] is False


def migration_setup(tmp_path, monkeypatch):
    home = tmp_path / "user profile"
    state = home / ".origin-agent"
    marketplace = home / ".agents/plugins/marketplace.json"
    marketplace.parent.mkdir(parents=True)
    other = {"name": "other", "source": {"source": "local", "path": "./plugins/other"}}
    original = {
        "name": "personal",
        "interface": {"displayName": "Personal"},
        "plugins": [
            other,
            {
                "name": "origin-agent",
                "source": {"source": "local", "path": "./plugins/origin-agent"},
            },
        ],
    }
    marketplace.write_text(json.dumps(original), encoding="utf-8")
    config = home / ".codex/config.toml"
    config.parent.mkdir()
    config.write_text('model = "gpt-5.6-terra"\n[plugins."origin-agent@personal"]\nenabled = true\n')
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setattr(oc.shutil, "which", lambda _: "codex")
    monkeypatch.setattr(
        oc,
        "registered_app",
        lambda *_: {
            "registered_app_available": True,
            "tool_names": ["origin_status"],
            "model_called": False,
        },
    )
    return home, state, marketplace, config, original


def test_consolidation_preserves_other_plugins_and_is_idempotent(tmp_path, monkeypatch):
    home, state, marketplace, config, original = migration_setup(tmp_path, monkeypatch)
    before = config.read_bytes()
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        config.write_text('model = "gpt-5.6-terra"\n')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(oc.subprocess, "run", run)
    result = oc.connect_openai(state, URL, retire_local=True)
    assert calls == [["codex", "plugin", "remove", "origin-agent@personal"]]
    catalog = json.loads(marketplace.read_text())
    assert catalog["plugins"] == original["plugins"][:1]
    assert catalog["interface"] == original["interface"]
    assert result["retired_local_entry"] is True
    again = oc.connect_openai(state, URL, retire_local=True)
    assert again["retired_local_entry"] is False
    assert len(calls) == 1
    # Undo the second binding before the migration receipt.
    rollback(state, again["receipt_id"])
    rollback(state, result["receipt_id"])
    assert json.loads(marketplace.read_text()) == original
    assert config.read_bytes() == before


def test_unavailable_cloud_app_leaves_all_old_settings_untouched(tmp_path, monkeypatch):
    _, state, marketplace, config, _ = migration_setup(tmp_path, monkeypatch)
    before = marketplace.read_bytes(), config.read_bytes()

    def unavailable(*_):
        raise ValueError("unavailable")

    monkeypatch.setattr(oc, "registered_app", unavailable)
    with pytest.raises(ValueError, match="unavailable"):
        oc.connect_openai(state, URL, retire_local=True)
    assert (marketplace.read_bytes(), config.read_bytes()) == before
    assert not (state / "openai-connection.json").exists()


def test_failed_cli_restores_files_and_keeps_marketplace(tmp_path, monkeypatch):
    _, state, marketplace, config, _ = migration_setup(tmp_path, monkeypatch)
    before = marketplace.read_bytes(), config.read_bytes()

    def failed(*args, **kwargs):
        config.write_text("# partial CLI edit\n")
        return SimpleNamespace(returncode=1, stderr=b"cache in use")

    monkeypatch.setattr(oc.subprocess, "run", failed)
    with pytest.raises(RuntimeError, match="could not retire"):
        oc.connect_openai(state, URL, retire_local=True)
    assert (marketplace.read_bytes(), config.read_bytes()) == before
    assert not (state / "openai-connection.json").exists()


def test_unfamiliar_direct_mcp_is_never_removed(tmp_path, monkeypatch):
    _, state, _, config, _ = migration_setup(tmp_path, monkeypatch)
    config.write_text('[mcp_servers.origin-agent]\ncommand = "custom-server"\nargs = []\n')
    with pytest.raises(ValueError, match="unfamiliar"):
        oc.connect_openai(state, URL, retire_local=True)
    assert not state.exists()


@pytest.mark.parametrize(
    "app",
    [
        {"id": APP, "name": "Different plugin", "toolSummaries": []},
        {"id": APP, "name": "Origin Companion", "toolSummaries": []},
        {"id": "asdk_app_" + "b" * 32, "name": "Origin Companion", "toolSummaries": []},
    ],
)
def test_registered_metadata_must_match_identity_and_enabled_tools(app, monkeypatch):
    class Process:
        stdin = io.StringIO()
        stdout = io.StringIO(
            json.dumps({"id": 1, "result": {}})
            + "\n"
            + json.dumps({"id": 2, "result": {"apps": [app]}})
            + "\n"
        )

        def terminate(self):
            pass

        def wait(self, timeout):
            pass

    monkeypatch.setattr(oc.subprocess, "Popen", lambda *a, **k: Process())
    with pytest.raises(ValueError):
        oc.registered_app(APP, "codex")


@pytest.mark.anyio
@pytest.mark.parametrize("profile", ["economy", "full"])
async def test_transports_advertise_the_same_public_brand(tmp_path, profile):
    from origin_agent import __version__
    from origin_agent.product import ICON_URL

    async with Client(make_server(Store(tmp_path), profile=profile)) as client:
        info = client.server_info
        assert info.name == "origin-agent"
        assert info.title == "Origin Companion"
        assert info.version == __version__
        assert info.icons[0].src == ICON_URL
        assert info.icons[0].mime_type == "image/png"


def test_owned_legacy_direct_entry_is_removed_by_official_cli(tmp_path, monkeypatch):
    home, state, marketplace, config, _ = migration_setup(tmp_path, monkeypatch)
    executable = state / "app/0.2.8/server/origin-agent.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"fixture")
    config.write_text(
        "[mcp_servers.origin-agent]\ncommand = " + json.dumps(str(executable)) + '\nargs = ["serve"]\n'
    )
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        config.write_text("# unrelated settings retained by the CLI\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(oc.subprocess, "run", run)
    result = oc.connect_openai(state, URL, retire_local=True)
    assert result["retired_direct_mcp"] is True
    assert [call[1:3] for call in calls] == [["mcp", "remove"], ["plugin", "remove"]]


def test_concurrent_catalog_edit_is_not_overwritten(tmp_path, monkeypatch):
    _, state, marketplace, config, original = migration_setup(tmp_path, monkeypatch)

    def run(args, **kwargs):
        changed = {**original, "new_user_setting": True}
        marketplace.write_text(json.dumps(changed))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(oc.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="marketplace changed"):
        oc.connect_openai(state, URL, retire_local=True)
    assert json.loads(marketplace.read_text())["new_user_setting"] is True
    assert not (state / "openai-connection.json").exists()
