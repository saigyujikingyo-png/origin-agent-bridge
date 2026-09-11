"""Read only our entries from installed hosts and test their actual stdio commands."""

import asyncio
import json
import os
from pathlib import Path

from mcp import Client, StdioServerParameters


async def main():
    home = Path.home()
    paths = {
        "claude_desktop": Path(os.environ["APPDATA"]) / "Claude/claude_desktop_config.json",
        "workbuddy": home / ".workbuddy/mcp.json",
        "codex_plugin": home / ".codex/plugins/cache/personal/origin-agent/0.1.0/.mcp.json",
    }
    result = {}
    for host, path in paths.items():
        config = json.loads(path.read_text(encoding="utf-8-sig"))["mcpServers"]["origin-agent"]
        async with Client(
            StdioServerParameters(command=config["command"], args=config["args"], env=config.get("env"))
        ) as client:
            tools = await client.list_tools()
            status = await client.call_tool("origin_status", {})
            assert not status.is_error
            assert len(tools.tools) == 8
            result[host] = {
                "configured_command_passed": True,
                "tool_count": len(tools.tools),
                "inbox": status.structured_content["inbox"],
                "host_model_invocation_tested": False,
            }
    output = home / ".origin-agent/verification/host-commands.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
