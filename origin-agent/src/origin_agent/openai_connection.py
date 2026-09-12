"""One private registered OpenAI app, shared by Chat, Work and Codex.

No model calls, credentials or public gateway. Local MCP remains a host adapter
for other agents. Account-specific connection IDs never belong in a release.
"""

import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

from .installation import Changes, contents, digest, encoded, rollback
from .storage import read_json

DIRECTORY_URL = "https://chatgpt.com/plugins?view=personal"
APP_ID = re.compile(r"asdk_app_[a-f0-9]{32}")


def normalise_connection(value):
    value = value.strip()
    if value.startswith("https://"):
        parsed = urlsplit(value)
        if parsed.netloc != "chatgpt.com" or parsed.username or parsed.password:
            raise ValueError("Use your own Origin Companion link from https://chatgpt.com/plugins.")
        match = re.fullmatch(r"/plugins/plugin_(asdk_app_[a-f0-9]{32})/?", parsed.path)
        if not match:
            raise ValueError(
                "Copy the Origin Companion plugin details link, not a conversation or tunnel URL."
            )
        app_id = match[1]
    else:
        app_id = value.removeprefix("plugin_")
    if not APP_ID.fullmatch(app_id):
        raise ValueError("Use a registered Origin Companion plugin link; API keys are not accepted here.")
    return {
        "schema_version": 1,
        "app_id": app_id,
        "plugin_url": f"https://chatgpt.com/plugins/plugin_{app_id}",
        "transport": "registered_openai_app",
    }


def connection_info(state_root):
    path = Path(state_root) / "openai-connection.json"
    if not path.exists():
        return {"configured": False, "plugin_url": DIRECTORY_URL}
    value = read_json(path)
    return {"configured": True, **normalise_connection(value["app_id"])}


def registered_app(app_id, command):
    """Use the installed Codex read-only protocol; never start a model turn."""
    process = subprocess.Popen(
        [command, "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    messages = queue.Queue()

    def reader():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                continue
        messages.put(None)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    def request(number, method, params, timeout):
        process.stdin.write(json.dumps({"id": number, "method": method, "params": params}) + "\n")
        process.stdin.flush()
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("OpenAI connection check timed out; the old entry was preserved.")
            try:
                message = messages.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError(
                    "OpenAI connection check timed out; the old entry was preserved."
                ) from None
            if message is None:
                raise RuntimeError("Codex closed the connection check; the old entry was preserved.")
            if message.get("id") == number:
                if "error" in message:
                    raise RuntimeError("Codex could not verify the registered app; reconnect it first.")
                return message.get("result", {})

    try:
        request(
            1,
            "initialize",
            {
                "clientInfo": {"name": "origin_companion_setup", "version": "1.0.0"},
                "capabilities": {"experimentalApi": True},
            },
            10,
        )
        process.stdin.write('{"method":"initialized","params":{}}\n')
        process.stdin.flush()
        result = request(2, "app/read", {"appIds": [app_id], "includeTools": True}, 35)
        found = [app for app in result.get("apps", []) if app.get("id") == app_id]
        if len(found) != 1:
            raise ValueError("This app is unavailable to the signed-in Codex account. Connect it first.")
        app = found[0]
        available = {t["name"] for t in app.get("toolSummaries", []) if t.get("isEnabled")}
        if app.get("name") != "Origin Companion" or not {
            "origin_status",
            "origin_help",
            "origin_call",
        }.issubset(available):
            raise ValueError("The link does not expose the expected enabled Origin Companion tools.")
        return {"registered_app_available": True, "tool_names": sorted(available), "model_called": False}
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        thread.join(timeout=1)
        process.stdin.close()
        process.stdout.close()


def connect_openai(state_root, value, *, retire_local=False, user_home=None):
    profile = normalise_connection(value)
    user_home = Path(user_home or Path.home()).resolve()
    marketplace = user_home / ".agents/plugins/marketplace.json"
    original = contents(marketplace)
    catalog = json.loads(original.decode("utf-8-sig")) if original is not None else {"plugins": []}
    entries = catalog.get("plugins")
    if not isinstance(entries, list):
        raise ValueError("Invalid personal marketplace; no settings were changed.")
    duplicate = [p for p in entries if p.get("name") == "origin-agent"]
    config_path = user_home / ".codex/config.toml"
    config_raw = contents(config_path)
    config_value = tomllib.loads(config_raw.decode("utf-8-sig")) if config_raw else {}
    direct = config_value.get("mcp_servers", {}).get("origin-agent")
    if retire_local and direct:
        executable = Path(direct.get("command", ""))
        if not (
            executable.is_absolute()
            and executable.name.lower() == "origin-agent.exe"
            and Path(state_root).resolve() in executable.resolve().parents
            and direct.get("args") == ["serve"]
        ):
            raise ValueError("An unfamiliar direct Origin MCP configuration was preserved for review.")
    verification = {"registered_app_available": None, "model_called": False}
    command = None
    if retire_local and (duplicate or direct):
        if user_home != Path.home().resolve() or os.environ.get("CODEX_HOME"):
            raise ValueError("Automatic consolidation requires the default Codex user profile.")
        if duplicate and (
            len(duplicate) != 1
            or catalog.get("name") != "personal"
            or duplicate[0].get("source") != {"source": "local", "path": "./plugins/origin-agent"}
        ):
            raise ValueError("Unexpected Origin marketplace entry; it was preserved for manual review.")
        command = shutil.which("codex")
        if not command:
            raise RuntimeError("Open Codex once so its CLI is available, then retry consolidation.")
        verification = registered_app(profile["app_id"], command)
    changes = Changes(state_root)
    try:
        changes.put(Path(state_root) / "openai-connection.json", encoded(profile))
        if command:
            config = config_path
            item = changes.prepare(config, contents(config))
            try:
                commands = []
                if direct:
                    commands.append([command, "mcp", "remove", "origin-agent"])
                if duplicate:
                    commands.append([command, "plugin", "remove", "origin-agent@personal"])
                for args in commands:
                    result = subprocess.run(
                        args,
                        capture_output=True,
                        timeout=60,
                        check=False,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    if result.returncode:
                        break
            finally:
                item["after"] = digest(contents(config))
                changes.save()
            if result.returncode:
                changes.value["host_cli_error"] = result.stderr.decode("utf-8", errors="replace")[:4000]
                changes.save()
                raise RuntimeError(
                    "Codex could not retire the local entry. Close old Origin Companion tasks and retry; "
                    "the installation receipt contains the CLI error. Saved configuration will be restored."
                )
            if contents(marketplace) != original:
                raise RuntimeError("The marketplace changed during consolidation; retry after reviewing it.")
            catalog["plugins"] = [p for p in entries if p.get("name") != "origin-agent"]
            # This is a targeted migration, not a generic marketplace editor.
            # Preserve the source folder for rollback; remove only its duplicate catalog entry.
            if duplicate:
                changes.put(marketplace, encoded(catalog))
        changes.value.update(
            status="installed",
            kind="openai_connection",
            profile=profile,
            retired_local_entry=bool(command and duplicate),
            retired_direct_mcp=bool(command and direct),
            verification=verification,
        )
        changes.save()
    except Exception:
        rollback(state_root, changes.root.name)
        raise
    return {
        **profile,
        **verification,
        "receipt_id": changes.root.name,
        "retired_local_entry": bool(command and duplicate),
        "retired_direct_mcp": bool(command and direct),
        "host_workflow_verified": False,
        "next_step": "Use this same plugin in a new Chat, cloud/local Work or Codex task. "
        "Keep your licensed Origin computer and private connection running.",
    }
