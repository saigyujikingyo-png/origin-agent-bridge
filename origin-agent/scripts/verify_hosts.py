"""Read only our entries from installed hosts and test their actual stdio commands."""

import argparse
import asyncio
import json
import os
import shutil
from pathlib import Path

from mcp import Client, StdioServerParameters

from origin_agent import __version__
from origin_agent.openai_connection import connection_info, registered_app


async def main():
    home = Path.home()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--codex-plugin",
        type=Path,
    )
    parser.add_argument("--hosts", default="claude_desktop,workbuddy,openai")
    args = parser.parse_args()
    selected = args.hosts.split(",")
    if set(selected) - {"claude_desktop", "workbuddy", "openai", "codex_plugin"}:
        parser.error("Unknown host; use claude_desktop,workbuddy,openai,codex_plugin")
    if "codex_plugin" in selected and args.codex_plugin is None:
        candidates = []
        root = home / ".codex/plugins/cache/personal/origin-agent"
        for manifest in root.glob("*/.codex-plugin/plugin.json"):
            version = json.loads(manifest.read_text(encoding="utf-8-sig")).get("version", "")
            if version.split("+")[0] == __version__:
                candidates.append(manifest.parent.parent)
        if len(candidates) != 1:
            raise ValueError("Provide --codex-plugin with the installed cache directory for this version")
        args.codex_plugin = candidates[0]
    paths = {
        "claude_desktop": Path(os.environ["APPDATA"]) / "Claude/claude_desktop_config.json",
        "workbuddy": home / ".workbuddy/mcp.json",
    }
    if args.codex_plugin is not None:
        paths["codex_plugin"] = args.codex_plugin / ".mcp.json"
    result = {}
    if "openai" in selected:
        profile = connection_info(home / ".origin-agent")
        command = shutil.which("codex")
        if not profile["configured"] or not command:
            raise ValueError("Connect the registered OpenAI app first, or select only local adapters")
        result["openai"] = {
            **registered_app(profile["app_id"], command),
            "host_model_invocation_tested": False,
            "runtime_version_verified": False,
        }
    for host, path in paths.items():
        if host not in selected:
            continue
        config = json.loads(path.read_text(encoding="utf-8-sig"))["mcpServers"]["origin-agent"]
        async with Client(
            StdioServerParameters(command=config["command"], args=config["args"], env=config.get("env"))
        ) as client:
            tools = await client.list_tools()
            status = await client.call_tool("origin_status", {})
            assert not status.is_error
            assert status.structured_content["plugin_version"] == __version__
            mode = status.structured_content["agent_profile"]["mode"]
            assert len(tools.tools) == (5 if mode == "economy" else 14)
            result[host] = {
                "configured_command_passed": True,
                "tool_count": len(tools.tools),
                "profile": mode,
                "version": status.structured_content["plugin_version"],
                "inbox": status.structured_content["inbox"],
                "host_model_invocation_tested": False,
            }
    output = home / ".origin-agent/verification/host-commands.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
