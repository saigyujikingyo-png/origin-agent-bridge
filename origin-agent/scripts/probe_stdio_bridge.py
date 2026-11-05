"""Opt-in frozen frontend probe. Fresh state only; tools/list, no native science."""

import argparse
import asyncio
import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path

import psutil

from origin_agent.stdio_binding import create_binding, digest
from origin_agent.storage import read_json


def memory(process):
    owner = psutil.Process(process.pid)
    members = [owner, *owner.children(recursive=True)]
    values = [member.memory_info() for member in members if member.is_running()]
    return {
        "owned_process_count": len(values),
        "working_set_bytes": sum(value.rss for value in values),
        "private_bytes": sum(value.private for value in values),
    }


def raw_probe(bridge, binding, root, modern):
    root.mkdir()
    state = root / "diagnostic.json"
    output = queue.Queue()
    with (root / "stderr.log").open("wb") as errors:
        process = subprocess.Popen(
            [
                str(bridge),
                "serve",
                "--binding",
                str(binding),
                "--idle-seconds",
                "1",
                "--diagnostic",
                str(state),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            env={**os.environ, "ORIGIN_AGENT_HOME": str(root)},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        def reader():
            for line in process.stdout:
                output.put(json.loads(line))

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        sequence = 0

        def send(value):
            process.stdin.write(json.dumps(value).encode() + b"\n")
            process.stdin.flush()

        def request(method, params):
            nonlocal sequence
            sequence += 1
            send({"jsonrpc": "2.0", "id": sequence, "method": method, "params": params})
            while True:
                answer = output.get(timeout=20)
                if answer.get("id") == sequence:
                    if "error" in answer:
                        raise RuntimeError(
                            "Isolated frozen protocol call failed: " + json.dumps(answer["error"])
                        )
                    return answer["result"]

        meta = (
            {
                "_meta": {
                    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientInfo": {"name": "isolated-bridge-probe", "version": "1"},
                    "io.modelcontextprotocol/clientCapabilities": {},
                }
            }
            if modern
            else {}
        )
        try:
            if modern:
                request("server/discover", meta)
            else:
                request(
                    "initialize",
                    {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "isolated-bridge-probe", "version": "1"},
                    },
                )
                send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            tools = request("tools/list", meta)
            active = memory(process)
            if modern:
                time.sleep(1.5)
            else:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if state.exists() and read_json(state).get("phase") == "cold":
                        break
                    time.sleep(0.05)
                else:
                    raise RuntimeError("Frozen frontend did not reach verified idle retirement")
                request("ping", {})
            idle = memory(process)
            before_wake = read_json(state)
            started = time.monotonic()
            repeated = request("tools/list", meta)
            wake_seconds = time.monotonic() - started
            assert repeated == tools
            time.sleep(0.1)
            after_wake = read_json(state)
            assert before_wake["backend_generation"] == 1
            assert after_wake["backend_generation"] == (1 if modern else 2)
        finally:
            process.stdin.close()
            # No force-kill: a timeout leaves an explicit failed probe for inspection.
            code = process.wait(timeout=10)
            thread.join(timeout=1)
            process.stdout.close()
        assert code == 0
        assert not list((root / "jobs").glob("*"))
        assert not list((root / "sessions").glob("*"))
        return {
            "protocol": "modern" if modern else "legacy",
            "tool_count": len(tools["tools"]),
            "active": active,
            "idle": idle,
            "wake_seconds": round(wake_seconds, 3),
            "same_pipe_wake": not modern,
            "modern_retained": modern,
            "eof_exit_code": code,
            "native_jobs": 0,
            "native_sessions": 0,
        }


async def sdk_probe(bridge, binding, root, modern):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root.mkdir()
    parameters = StdioServerParameters(
        command=str(bridge),
        args=["serve", "--binding", str(binding), "--idle-seconds", "0.3"],
        env={**os.environ, "ORIGIN_AGENT_HOME": str(root)},
    )
    with (root / "stderr.log").open("w") as errors:
        async with stdio_client(parameters, errlog=errors) as streams:
            async with ClientSession(*streams, read_timeout_seconds=20) as session:
                await (session.discover() if modern else session.initialize())
                first = await session.list_tools()
                await asyncio.sleep(1)
                second = await session.list_tools()
                assert first == second
                return {"protocol": session.protocol_version, "tools": len(first.tools), "same_pipe": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--backend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"bridge_sha256": digest(args.bridge), "raw": [], "sdk_2_2_0": []}
    for profile in ("full", "economy"):
        binding = args.output / (profile + "-binding.json")
        created = create_binding(args.backend, ["serve", "--profile", profile], binding)
        report["engine_version"] = created["engine_version"]
        for modern in (False, True):
            label = profile + ("-modern" if modern else "-legacy")
            report["raw"].append(
                {"profile": profile, **raw_probe(args.bridge, binding, args.output / label, modern)}
            )
            (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            report["sdk_2_2_0"].append(
                {
                    "profile": profile,
                    **asyncio.run(sdk_probe(args.bridge, binding, args.output / (label + "-sdk"), modern)),
                }
            )
        (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
