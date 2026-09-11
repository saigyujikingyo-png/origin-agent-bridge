import json
import os
import sys

import pytest
from mcp import Client, StdioServerParameters

from origin_agent import __version__
from origin_agent.server import make_server


@pytest.mark.anyio
async def test_protocol_tools_and_schema_guard(store):
    async with Client(make_server(store), raise_exceptions=True) as client:
        tools = (await client.list_tools()).tools
        assert len(tools) == 14
        serialized = json.dumps([tool.model_dump(mode="json") for tool in tools])
        assert len(serialized) < 38000
        status = await client.call_tool("origin_status", {})
        assert not status.is_error
        assert status.structured_content["plugin_version"] == __version__
        program = next(t for t in tools if t.name == "origin_run_program")
        assert program.annotations.destructive_hint is True
        assert program.annotations.open_world_hint is True
        invalid = await client.call_tool("origin_plan_workflow", {"workflow": {"python": "1+1"}})
        assert invalid.is_error


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
@pytest.mark.parametrize("profile", ["full", "economy"])
async def test_real_stdio_transport(store, mode, profile):
    environment = {**os.environ, "ORIGIN_AGENT_HOME": str(store.root)}
    async with Client(
        StdioServerParameters(
            command=sys.executable,
            args=["-m", "origin_agent", "serve", "--profile", profile],
            env=environment,
        ),
        mode=mode,
    ) as client:
        assert len((await client.list_tools()).tools) == (5 if profile == "economy" else 14)
        answer = await client.call_tool("origin_status", {})
        assert not answer.is_error
        source = store.root / "inbox" / "cached-tools.csv"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("X,Y\n0,1\n1,3\n2,5\n", encoding="utf-8")
        inspected = await client.call_tool("origin_inspect_dataset", {"path": str(source)})
        assert not inspected.is_error
        plan = await client.call_tool(
            "origin_plan_workflow",
            {
                "workflow": {
                    "panels": [
                        {"dataset_id": inspected.structured_content["dataset_id"], "x": "X", "y": ["Y"]}
                    ]
                }
            },
        )
        assert not plan.is_error
