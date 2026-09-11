"""Measure protocol context size locally. These bytes are not provider-billed token counts."""

import argparse
import asyncio
import json
from pathlib import Path

from origin_agent import __version__
from origin_agent.server import make_server
from origin_agent.storage import Store


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"version": __version__, "metric": "UTF-8 bytes of compact JSON MCP tool definitions"}
    for mode in ("full", "economy"):
        tools = await make_server(Store(), profile=mode, preset="generic").list_tools()
        payload = json.dumps(
            [t.model_dump(mode="json", by_alias=True) for t in tools],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        report[mode] = {"tools": len(tools), "bytes": len(payload.encode("utf-8"))}
    report["tool_definition_reduction_percent"] = round(
        100 * (1 - report["economy"]["bytes"] / report["full"]["bytes"]),
        2,
    )
    report["billing_tokens_measured"] = False
    report["model_success_rate_measured"] = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
