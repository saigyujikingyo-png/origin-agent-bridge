import json
import os
import sys

import pytest
from mcp import Client, StdioServerParameters

from origin_agent.server import make_server


@pytest.mark.anyio
async def test_protocol_tools_and_schema_guard(store):
    async with Client(make_server(store), raise_exceptions=True) as client:
        tools = (await client.list_tools()).tools
        assert len(tools) == 8
        serialized = json.dumps([tool.model_dump(mode="json") for tool in tools])
        assert len(serialized) < 23000
        status = await client.call_tool("origin_status", {})
        assert not status.is_error
        assert status.structured_content["plugin_version"] == "0.1.0"
        invalid = await client.call_tool("origin_plan_workflow", {"workflow": {"python": "1+1"}})
        assert invalid.is_error


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_real_stdio_transport(store, mode):
    environment = {**os.environ, "ORIGIN_AGENT_HOME": str(store.root)}
    async with Client(
        StdioServerParameters(command=sys.executable, args=["-m", "origin_agent", "serve"], env=environment),
        mode=mode,
    ) as client:
        assert len((await client.list_tools()).tools) == 8
        answer = await client.call_tool("origin_status", {})
        assert not answer.is_error
