"""Frozen-runtime cloud-table regression; synthetic data, no model or cloud calls."""

import argparse
import asyncio
import base64
import hashlib
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
        import platform

        assert evidence["status"]["device"]["computer_name"] == platform.node()
        evidence["device_identity_matches_process"] = True
        bad_project = root / "inbox" / "invalid-project.csv"
        bad_project.write_text("x,y\n1,2\n", encoding="utf-8")
        invalid = await client.call_tool(
            "origin_call",
            {
                "operation": "origin_session",
                "arguments_json": json.dumps(
                    {
                        "action": "open",
                        "request_id": "reject-csv-project",
                        "project_path": str(bad_project),
                    }
                ),
            },
        )
        assert invalid.is_error
        assert invalid.structured_content == {
            "error": "invalid_request",
            "message": "Project inputs must be OPJ/OPJU",
        }
        assert json.loads(invalid.content[0].text) == invalid.structured_content
        assert not list((root / "sessions").iterdir())
        evidence["structured_error_verified_without_session"] = True

        receiver = await direct("origin_help", {"operation": "origin_get_artifact", "query": "receiver"})
        receiver_source = receiver["receiver"]["javascript"]
        expected_receiver = Path(__file__).resolve().parents[1] / "src/origin_agent/data/receive_artifact.js"
        assert receiver_source == expected_receiver.read_text(encoding="utf-8")
        evidence["receiver_sha256"] = hashlib.sha256(receiver_source.encode("utf-8")).hexdigest()
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
            "title": "Synthetic K₂CrO₄ cloud-table Beer-Lambert regression",
            "x_label": "Concentration, c / mol dm⁻³",
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
        evidence["binary_downloads"] = []
        for entry in job["artifacts"]:
            if entry["name"] not in {"project.opju", "panel-01.png", "panel-01.pdf", "panel-01.svg"}:
                continue
            download = await client.call_tool(
                "origin_get_artifact",
                {"artifact_id": job["job_id"] + "/" + entry["name"], "mode": "download"},
            )
            assert not download.is_error, download
            resource = next(c.resource for c in download.content if c.type == "resource")
            binary = base64.b64decode(resource.blob, validate=True)
            assert len(binary) == entry["bytes"] and hashlib.sha256(binary).hexdigest() == entry["sha256"]
            evidence["binary_downloads"].append(
                {"name": entry["name"], "sha256": entry["sha256"], "bytes": len(binary)}
            )
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
