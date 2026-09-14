"""Native regression of WorkBuddy feedback; protocol evidence, not an LLM benchmark."""

import argparse
import asyncio
import base64
import hashlib
import json
import math
import os
import statistics
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
    if root.exists():
        raise ValueError("Use a fresh acceptance directory to avoid reusing past results")
    (root / "inbox").mkdir(parents=True)
    received = root / "received"
    received.mkdir()
    xs = [2e-5 * i for i in range(1, 7)]
    noise = [0.001, -0.001, 0.0005, -0.0005, 0.0008, -0.0008]
    ys = [3000 * x + 0.012 + e for x, e in zip(xs, noise, strict=True)]
    source = root / "inbox/synthetic-feedback.csv"
    source.write_text(
        "concentration_M,concentration_mM,absorbance,replicate,SD\n"
        + "".join(
            f"{x:.12g},{x * 1000:.12g},{y:.12g},{y + 0.04:.12g},0.002\n" for x, y in zip(xs, ys, strict=True)
        ),
        encoding="utf-8",
    )
    expected = statistics.linear_regression(xs, ys)
    env = {**os.environ, "ORIGIN_AGENT_HOME": str(root)}
    if args.exe:
        env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
    argv = (["serve"] if args.exe else ["-m", "origin_agent", "serve"]) + ["--profile", "economy"]
    evidence = {"actual_model_tested": False, "billing_tokens_measured": False, "calls": 0}
    started = time.monotonic()
    async with Client(
        StdioServerParameters(command=args.exe or sys.executable, args=argv, env=env)
    ) as client:

        async def raw(name, arguments):
            evidence["calls"] += 1
            return await client.call_tool(name, arguments)

        async def direct(name, arguments):
            answer = await raw(name, arguments)
            assert not answer.is_error, answer
            return answer.structured_content

        async def call(name, arguments):
            return await direct("origin_call", {"operation": name, "arguments_json": json.dumps(arguments)})

        assert len((await client.list_tools()).tools) == 5
        evidence["status"] = await direct("origin_status", {})
        evidence["plugin_version"] = evidence["status"]["plugin_version"]
        assert "no specific model is required" in evidence["status"]["agent_profile"]["host_requirement"]
        direct_help = await direct("origin_help", {"operation": "origin_get_job"})
        assert await call("origin_help", {"operation": "origin_get_job"}) == direct_help
        evidence["misrouted_help_recovered"] = True
        dataset = await call("origin_inspect_dataset", {"path": str(source)})
        bad = await raw(
            "origin_recipe",
            {
                "dataset_id": dataset["dataset_id"],
                "x": "concentration_M",
                "y": ["absorbance"],
                "recipe": "beer_lambert",
                "action": "run",
                "intercept": "free",
                "weighting": "none",
                "concentration_scale_molar": 1,
            },
        )
        assert bad.is_error
        evidence["missing_paired_parameter_rejected"] = True
        common = {"dataset_id": dataset["dataset_id"], "x": "concentration_M", "y": ["absorbance"]}
        analysis = {
            "kind": "beer_lambert",
            "intercept": "free",
            "weighting": "none",
            "unknown_absorbance": 0.2,
            "path_length_cm": 2,
            "concentration_scale_molar": 1,
        }
        workflow = {
            "panels": [
                {
                    **common,
                    "title": "Synthetic noisy calibration - automatic notation",
                    "analysis": analysis,
                    "style": {"x_label": "Concentration / mol dm⁻³", "y_label": "Absorbance"},
                },
                {
                    **common,
                    "x": "concentration_mM",
                    "title": "Unit conversion and extrapolation",
                    "analysis": {**analysis, "unknown_absorbance": 1.0, "concentration_scale_molar": 0.001},
                    "style": {"x_label": "Concentration / mmol dm⁻³", "y_label": "Absorbance"},
                },
                {
                    **common,
                    "title": "Explicit decimal ticks and supplied error bars",
                    "y": ["absorbance", "replicate"],
                    "y_errors": {"absorbance": "SD", "replicate": "SD"},
                    "style": {
                        "x_tick_format": "decimal",
                        "y_tick_format": "scientific",
                        "x_label": "Concentration / mol dm⁻³",
                        "y_label": "Absorbance",
                    },
                },
            ],
            "formats": ["png", "pdf", "svg"],
        }
        plan = await call("origin_plan_workflow", {"workflow": workflow})
        job = await call("origin_run_workflow", {"plan_id": plan["plan_id"]})
        repeat = await call("origin_run_workflow", {"plan_id": plan["plan_id"]})
        assert job["job_id"] == repeat["job_id"]
        evidence["duplicate_job_reused"] = True
        deadline = time.monotonic() + 240
        while job["state"] not in ("succeeded", "failed", "cancelled", "interrupted"):
            assert time.monotonic() < deadline, "Native regression exceeded its deadline"
            job = await call("origin_get_job", {"job_id": job["job_id"], "wait_seconds": 20})
            print(
                json.dumps({"job": job["job_id"], "state": job["state"], "progress": job.get("progress")}),
                flush=True,
            )
        assert job["state"] == "succeeded", job
        manifest = json.loads((root / "jobs" / job["job_id"] / "manifest.json").read_text("utf-8"))
        first, second = manifest["summary"]
        assert math.isclose(first["slope"], expected.slope, rel_tol=1e-9)
        assert math.isclose(first["intercept"], expected.intercept, rel_tol=1e-9)
        assert math.isclose(second["slope"] * 1000, first["slope"], rel_tol=1e-9)
        assert math.isclose(first["molar_absorptivity_L_mol_cm"], expected.slope / 2, rel_tol=1e-9)
        assert math.isclose(second["molar_absorptivity_L_mol_cm"], expected.slope / 2, rel_tol=1e-9)
        assert math.isclose(
            first["unknown_concentration_in_x_units"],
            (0.2 - expected.intercept) / expected.slope,
            rel_tol=1e-9,
        )
        assert first["extrapolation"] is False and second["extrapolation"] is True
        for summary in manifest["summary"]:
            assert isinstance(summary["unknown_uncertainty"], str)
            assert summary["unknown_uncertainty_result"] == {
                "status": "not_calculated",
                "value": None,
                "reason": "inverse_calibration_uncertainty_not_supported",
                "method": None,
            }
        verification = manifest["verification"]
        assert verification["axis_tick_format_roundtrip"]
        ticks = [v["properties"] for v in verification["axis_tick_formats"]]
        assert ticks[0]["x.label.numFormat"] == 2
        assert ticks[1]["x.label.numFormat"] == 1
        assert ticks[2]["x.label.numFormat"] == 1 and ticks[2]["y.label.numFormat"] == 2
        receipts = []
        for artifact in manifest["artifacts"]:
            answer = await raw(
                "origin_get_artifact",
                {"artifact_id": job["job_id"] + "/" + artifact["name"], "mode": "download"},
            )
            assert not answer.is_error, answer
            resource = next(item.resource for item in answer.content if item.type == "resource")
            blob = base64.b64decode(resource.blob, validate=True)
            assert len(blob) == artifact["bytes"]
            assert hashlib.sha256(blob).hexdigest() == artifact["sha256"]
            target = received / artifact["name"]
            target.write_bytes(blob)
            assert hashlib.sha256(target.read_bytes()).hexdigest() == artifact["sha256"]
            receipts.append({"name": target.name, "bytes": len(blob), "sha256": artifact["sha256"]})
        evidence.update(
            job_id=job["job_id"],
            summary=manifest["summary"],
            verification=verification,
            received=receipts,
            passed=True,
            end_to_end_seconds=round(time.monotonic() - started, 3),
        )
    (root / "acceptance-workbuddy-fixes.json").write_text(json.dumps(evidence, indent=2), "utf-8")
    print(
        json.dumps(
            {
                "passed": True,
                "artifacts_received": len(receipts),
                "seconds": evidence["end_to_end_seconds"],
                "evidence": str(root / "acceptance-workbuddy-fixes.json"),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
