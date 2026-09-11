"""Real native acceptance through MCP, with synthetic fixtures and immutable evidence."""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from mcp import Client, StdioServerParameters


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe")
    parser.add_argument("--home", required=True)
    args = parser.parse_args()
    root = Path(args.home).resolve()
    root.mkdir(parents=True, exist_ok=True)
    data = root / "inbox"
    data.mkdir(exist_ok=True)
    source = data / "synthetic-calibration.csv"
    source.write_text(
        "Concentration,Absorbance,Replicate,SD\n0,0.104,0.2,0.01\n1,0.290,0.4,0.02\n"
        "2,0.500,0.6,0.01\n3,0.710,0.8,0.02\n4,0.896,1.0,0.01\n",
        encoding="utf-8",
    )
    command = args.exe or sys.executable
    argv = ["serve"] if args.exe else ["-m", "origin_agent", "serve"]
    environment = {**os.environ, "ORIGIN_AGENT_HOME": str(root)}
    if args.exe:
        environment["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
    started = time.monotonic()
    async with Client(StdioServerParameters(command=command, args=argv, env=environment)) as client:

        async def call(name, arguments):
            answer = await client.call_tool(name, arguments)
            if answer.is_error:
                raise RuntimeError(answer.content)
            return answer.structured_content

        tools = await client.list_tools()
        cold_seconds = time.monotonic() - started
        status = await call("origin_status", {})
        inspected = await call("origin_inspect_dataset", {"path": str(source)})
        identifier = inspected["dataset_id"]
        common = {"dataset_id": identifier, "x": "Concentration", "y": ["Absorbance"]}
        workflow = {
            "panels": [
                {
                    **common,
                    "title": "Calibration - free intercept",
                    "y_errors": {"Absorbance": "SD"},
                    "style": {"x_label": "Concentration (mmol/L)", "y_label": "Absorbance"},
                    "analysis": {
                        "kind": "beer_lambert",
                        "intercept": "free",
                        "weighting": "none",
                        "unknown_absorbance": 0.6,
                        "path_length_cm": 1.0,
                        "concentration_scale_molar": 0.001,
                    },
                },
                {
                    **common,
                    "title": "Zero intercept verification",
                    "analysis": {"kind": "linear_fit", "intercept": "zero", "weighting": "none"},
                },
                {
                    **common,
                    "title": (
                        "Multiple series - 合成数据验收 - Long descriptive title with units and "
                        "uncertainty, preserving every requested word through PNG PDF SVG "
                        "and native project reopen"
                    )[:160],
                    "y": ["Absorbance", "Replicate"],
                    "style": {"plot": "line_symbol", "preset": "presentation"},
                },
            ],
            "formats": ["png", "pdf", "svg"],
        }
        plan = await call("origin_plan_workflow", {"workflow": workflow})
        job = await call("origin_run_workflow", {"plan_id": plan["plan_id"]})
        repeat = await call("origin_run_workflow", {"plan_id": plan["plan_id"]})
        assert repeat["job_id"] == job["job_id"]
        print(json.dumps({"job_id": job["job_id"], "cold_mcp_seconds": round(cold_seconds, 3)}), flush=True)
        while job["state"] not in ("succeeded", "failed", "cancelled", "interrupted"):
            job = await call("origin_get_job", {"job_id": job["job_id"], "wait_seconds": 20})
            print(
                json.dumps(
                    {"state": job["state"], "progress": job.get("progress"), "error": job.get("error")}
                ),
                flush=True,
            )
        assert job["state"] == "succeeded", job
        assert job["verification"]["graph_text_roundtrip"]
        assert job["verification"]["titles_reopened"] == len(workflow["panels"])
        project = await call("origin_inspect_project", {"job_id": job["job_id"]})
        preview = await client.call_tool(
            "origin_get_artifact", {"artifact_id": f"{job['job_id']}/panel-01.png", "mode": "preview"}
        )
        assert not preview.is_error and any(c.type == "image" for c in preview.content)
        evidence = {
            "tool_count": len(tools.tools),
            "schema_characters": len(json.dumps([t.model_dump(mode="json") for t in tools.tools])),
            "cold_mcp_seconds": round(cold_seconds, 3),
            "end_to_end_seconds": round(time.monotonic() - started, 3),
            "status": status,
            "job": job,
            "project": project,
            "preview_returned": True,
            "duplicate_job_reused": True,
        }
        (root / "acceptance.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(
            json.dumps({"evidence": str(root / "acceptance.json"), "verification": job["verification"]}),
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
