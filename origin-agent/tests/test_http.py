import asyncio
import os
import socket
import subprocess
import sys

import httpx2
import pytest
from mcp import Client


@pytest.mark.anyio
@pytest.mark.parametrize("profile", ["full", "economy"])
async def test_loopback_http_and_foreign_host_rejection(store, profile):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    child = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "origin_agent",
            "serve",
            "--profile",
            profile,
            "--transport",
            "streamable-http",
            "--port",
            str(port),
        ],
        env={**os.environ, "ORIGIN_AGENT_HOME": str(store.root)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        async with httpx2.AsyncClient() as http:
            for _ in range(100):
                try:
                    await http.get(f"http://127.0.0.1:{port}/")
                    break
                except httpx2.ConnectError:
                    await asyncio.sleep(0.1)
            response = await http.post(
                f"http://127.0.0.1:{port}/mcp",
                headers={"Host": "foreign.example"},
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            )
            assert response.status_code in (400, 403, 421)
        async with Client(f"http://127.0.0.1:{port}/mcp") as client:
            assert len((await client.list_tools()).tools) == (5 if profile == "economy" else 14)
            answer = await client.call_tool("origin_status", {})
            assert not answer.is_error
    finally:
        child.terminate()
        child.wait(timeout=10)
