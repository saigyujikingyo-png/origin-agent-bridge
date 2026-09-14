"""Real Origin via the compact MCP interface; synthetic data, no model API calls."""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from contract_validation import ContractClient as Client
from mcp import StdioServerParameters


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--exe")
    args = parser.parse_args()
    root = args.home.resolve()
    (root / "inbox").mkdir(parents=True, exist_ok=True)
    source = root / "inbox/synthetic-economy.csv"
    source.write_text("X,Y\n0,1\n1,3\n2,5\n3,7\n4,9\n", encoding="utf-8")
    env = {**os.environ, "ORIGIN_AGENT_HOME": str(root)}
    if args.exe:
        env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
    argv = ["serve"] if args.exe else ["-m", "origin_agent", "serve"]
    argv += ["--profile", "economy", "--model-preset", "generic", "--vision", "auto"]
    evidence = {"native_verified": False, "actual_model_tested": False, "jobs": []}
    started = time.monotonic()
    async with Client(
        StdioServerParameters(command=args.exe or sys.executable, args=argv, env=env)
    ) as client:

        async def direct(name, arguments):
            result = await client.call_tool(name, arguments)
            assert not result.is_error, result
            return result.structured_content

        async def call(operation, arguments):
            return await direct(
                "origin_call", {"operation": operation, "arguments_json": json.dumps(arguments)}
            )

        async def wait(job):
            deadline = time.monotonic() + 210
            while job["state"] not in ("succeeded", "failed", "cancelled", "interrupted"):
                assert time.monotonic() < deadline, job
                job = await call("origin_get_job", {"job_id": job["job_id"], "wait_seconds": 20})
                print(json.dumps({"job_id": job["job_id"], "state": job["state"]}), flush=True)
            assert job["state"] == "succeeded", job
            evidence["jobs"].append(job)
            return job

        assert len((await client.list_tools()).tools) == 5
        evidence["status"] = await direct("origin_status", {})
        help_result = await direct("origin_help", {"operation": "origin_inspect_dataset"})
        assert "path" in help_result["input_schema"]["properties"]
        dataset = await call("origin_inspect_dataset", {"path": str(source)})
        spec = {
            "dataset_id": dataset["dataset_id"],
            "x": "X",
            "y": ["Y"],
            "recipe": "linear_fit",
            "intercept": "free",
            "weighting": "none",
            "action": "run",
            "title": "Economy mode synthetic fit",
        }
        job = await direct("origin_recipe", spec)
        repeat = await direct("origin_recipe", spec)
        assert job["job_id"] == repeat["job_id"]
        first = await wait(job)
        project = await call("origin_inspect_project", {"job_id": first["job_id"]})
        evidence["project"] = project
        # Reconstruct bounded text pages and compare exactly with the verified local artifact.
        artifact_id = first["job_id"] + "/manifest.json"
        offset, text = 0, ""
        while True:
            response = await client.call_tool(
                "origin_get_artifact",
                {
                    "artifact_id": artifact_id,
                    "mode": "text",
                    "offset": offset,
                    "max_chars": 1000,
                },
            )
            assert not response.is_error, response
            page = json.loads(response.content[-1].text)
            text += page["text"]
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
        manifest = json.loads(text)
        local_manifest = json.loads((root / "jobs" / first["job_id"] / "manifest.json").read_text("utf-8"))
        assert manifest == local_manifest
        evidence["text_pagination_exact"] = True
        await direct("origin_help", {"operation": "origin_run_program"})
        second = await wait(
            await call(
                "origin_run_program",
                {
                    "program": {
                        "title": "Economy generic native readback",
                        "language": "python",
                        "code": "w=op.new_sheet('w', lname='Economy native')\nw.from_list(0,[7,14,21])\n"
                        "RESULTS['values']=w.to_list(0)\nassert RESULTS['values']==[7,14,21]\n",
                        "graph_formats": [],
                        "readbacks": {"sum": {"expression": "col(A)[1]+col(A)[2]+col(A)[3]", "expected": 42}},
                    }
                },
            )
        )
        evidence["program_result"] = json.loads(
            (root / "jobs" / second["job_id"] / "result.json").read_text("utf-8")
        )
        evidence["native_verified"] = True
    evidence["elapsed_seconds"] = round(time.monotonic() - started, 3)
    (root / "acceptance-economy.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps({"passed": True, "jobs": len(evidence["jobs"]), "elapsed": evidence["elapsed_seconds"]}))


if __name__ == "__main__":
    asyncio.run(main())
