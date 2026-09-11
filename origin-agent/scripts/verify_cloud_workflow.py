"""Frozen-runtime cloud-table regression; synthetic data, no model or cloud calls."""

import argparse
import asyncio
import json
import math
import os
import time
from pathlib import Path

from mcp import Client, StdioServerParameters

CSV = (
    "Concentration,Absorbance\n0.00002,0.118\n0.00004,0.208\n0.00008,0.407\n"
    "0.00012,0.592\n0.00016,0.791\n0.00020,0.979\n"
)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True)
    parser.add_argument("--home", type=Path, required=True)
    args = parser.parse_args()
    root = args.home.resolve()
    root.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "ORIGIN_AGENT_HOME": str(root)}
    env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
    for key in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(key, None)
    started = time.monotonic()
    evidence = {"actual_model_tested": False, "development_runtime_removed_from_path": True}
    async with Client(
        StdioServerParameters(command=args.exe, args=["serve", "--profile", "economy"], env=env)
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
            deadline = time.monotonic() + 180
            while not job["terminal"]:
                assert time.monotonic() < deadline, job
                job = await call("origin_get_job", {"job_id": job["job_id"], "wait_seconds": 20})
            assert "poll_after_seconds" not in job
            return job

        assert len((await client.list_tools()).tools) == 5
        evidence["status"] = await direct("origin_status", {})
        await direct("origin_help", {"operation": "origin_import_table"})
        dataset = await call("origin_import_table", {"content": CSV})
        replay = await call("origin_import_table", {"content": CSV})
        assert dataset["dataset_id"] == replay["dataset_id"]
        evidence["import_reused"] = True
        await direct("origin_help", {"operation": "origin_recipe"})
        recipe = {
            "dataset_id": dataset["dataset_id"],
            "x": "Concentration",
            "y": ["Absorbance"],
            "recipe": "beer_lambert",
            "action": "run",
            "intercept": "free",
            "weighting": "none",
            "unknown_absorbance": 0.366,
            "path_length_cm": 1,
            "concentration_scale_molar": 1,
            "title": "Synthetic cloud-table Beer-Lambert regression",
            "x_label": "Concentration, c / mol dm\\+(-3)",
            "y_label": "Absorbance, A",
            "formats": ["png", "pdf", "svg"],
        }
        job = await call("origin_recipe", recipe)
        repeat = await call("origin_recipe", recipe)
        assert job["job_id"] == repeat["job_id"]
        job = await wait(job)
        assert job["state"] == "succeeded", job
        evidence["success"] = job
        evidence["workflow_seconds"] = round(time.monotonic() - started, 3)
        assert job["verification"]["project_reopened"] and job["verification"]["data_roundtrip"]
        assert job["verification"]["graph_text_roundtrip"]
        rows = [[float(v) for v in line.split(",")] for line in CSV.splitlines()[1:]]
        mx, my = (sum(row[col] for row in rows) / len(rows) for col in (0, 1))
        slope = sum((x - mx) * (y - my) for x, y in rows) / sum((x - mx) ** 2 for x, y in rows)
        intercept = my - slope * mx
        result = job["summary"][0]
        for actual, expected in (
            (result["slope"], slope),
            (result["intercept"], intercept),
            (result["unknown_concentration_in_x_units"], (0.366 - intercept) / slope),
            (result["molar_absorptivity_L_mol_cm"], slope),
        ):
            assert math.isclose(actual, expected, rel_tol=1e-8, abs_tol=1e-12), (actual, expected)
        for name in ("project.opju", "panel-01.png", "panel-01.pdf", "panel-01.svg"):
            assert any(a["name"] == name and a["bytes"] > 0 for a in job["artifacts"])
        preview = await client.call_tool(
            "origin_get_artifact", {"artifact_id": job["job_id"] + "/panel-01.png", "mode": "preview"}
        )
        assert not preview.is_error and any(c.type == "image" for c in preview.content)
        evidence["independent_numeric_crosscheck"] = True
        evidence["preview_returned"] = True
        failure = await call(
            "origin_run_program",
            {
                "program": {
                    "title": "Deliberate missing dependency regression",
                    "language": "python",
                    "code": "import origin_companion_intentionally_missing_dependency",
                    "graph_formats": [],
                    "timeout_seconds": 30,
                }
            },
        )
        failure = await wait(failure)
        assert failure["state"] == "failed" and failure["diagnostic"]["type"] == "ModuleNotFoundError"
        assert "Stop polling" in failure["next_action"]
        assert failure["progress"]["stage"] == "failed"
        assert failure["recovery"]["kind"] == "missing_python_dependency"
        evidence["intentional_failure"] = failure
    evidence["seconds"] = round(time.monotonic() - started, 3)
    output = root / "acceptance-cloud-workflow.json"
    output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": True,
                "evidence": str(output),
                "workflow_seconds": evidence["workflow_seconds"],
                "job": job["job_id"],
                "seconds": evidence["seconds"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
