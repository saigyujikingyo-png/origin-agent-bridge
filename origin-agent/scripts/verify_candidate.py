"""Evaluate pinned upstream code through MCP against an owned Origin instance.

The candidate is optional and installed in a separate environment. This tests
its serial bridge with external Origin automation, not its embedded OPX launcher.
Run with the Origin Agent development environment (MCP 2); the candidate uses MCP 1.
"""

import argparse
import asyncio
import contextlib
import csv
import json
import math
import os
import subprocess
import time
from pathlib import Path

PIN = "fecb7226ed60d7651d921d2586eb9950bf16b618"


def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def worker(directory):
    from origin_mcp.bridge import OriginEmbeddedBridgeServer
    from origin_mcp.bridge_handshake import generate_token, write_handshake
    from origin_mcp.origin_client import OriginClient

    client = OriginClient()
    try:
        connected = client.connect(show=False)
        op = client.op
        engine = {
            "version": op.lt_float("@V"),
            "edition": "OriginPro" if op.lt_int("@IM") == 2 else "Origin",
            "demo": op.lt_int("@VM"),
            "bitness": op.lt_int("@VB"),
            "connected": connected,
            "embedded": not bool(op.config.oext),
        }
        write(directory / "engine.json", engine)
        assert math.isclose(engine["version"], 10.350243, abs_tol=1e-7, rel_tol=0)
        assert engine["demo"] == 0 and engine["bitness"] == 64
        # All Origin calls stay on this worker's main thread. No attach() is used.
        token = generate_token()
        with OriginEmbeddedBridgeServer(("127.0.0.1", 0), token=token, client=client) as server:
            write_handshake("127.0.0.1", server.server_address[1], token)
            server.serve_forever(poll_interval=0.05)
    finally:
        if client._op is not None:
            client.quit()


async def evaluate(args, directory, env):
    from mcp import Client, StdioServerParameters

    report = {
        "upstream": "https://github.com/Ge-Shun/origin-mcp",
        "commit": PIN,
        "mode": "upstream serial bridge, external owned Origin; OPX not tested",
        "host_model_invocation_tested": False,
        "steps": [],
        "checks": {},
        "ok": False,
    }
    report_path = directory / "candidate-report.json"
    source = directory / "synthetic.csv"
    with source.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", "decay", "linear"])
        for index in range(51):
            x = index / 10
            writer.writerow([x, 0.3 + 2 * math.exp(-x / 1.4), 0.1 + 0.2 * x])
    started = time.monotonic()
    params = StdioServerParameters(command=str(args.candidate_python), args=["-m", "origin_mcp"], env=env)
    try:
        async with Client(params) as client:
            catalog = (await client.list_tools()).tools
            report["tool_count"] = len(catalog)
            report["tool_schema_bytes"] = len(json.dumps([tool.model_dump() for tool in catalog]))
            selected = {
                "origin_create_matrix",
                "origin_get_matrix_info",
                "origin_read_matrix",
                "origin_set_cell_value",
                "origin_get_cell_value",
                "origin_get_graph_info",
                "origin_format_graph",
                "origin_nonlinear_fit_structured",
                "origin_smooth",
            }
            write(
                directory / "selected-schemas.json",
                {tool.name: tool.model_dump() for tool in catalog if tool.name in selected},
            )

            async def call(name, arguments, allow_failure=False):
                tick = time.monotonic()
                result = await asyncio.wait_for(client.call_tool(name, arguments), timeout=90)
                data = result.structured_content
                if data is None:
                    text = next(item.text for item in result.content if getattr(item, "type", "") == "text")
                    data = json.loads(text)
                value = data.get("data", {})
                semantic_ok = (
                    not result.is_error
                    and data.get("ok") is True
                    and value.get("executed") is not False
                    and value.get("result") is not False
                )
                step = {
                    "name": name,
                    "seconds": round(time.monotonic() - tick, 3),
                    "result": data,
                    "semantic_ok": semantic_ok,
                    "response_bytes": len(json.dumps(data).encode("utf-8")),
                }
                report["steps"].append(step)
                write(report_path, report)
                print(
                    json.dumps({"tool": name, "seconds": step["seconds"], "semantic_ok": semantic_ok}),
                    flush=True,
                )
                if not semantic_ok and not allow_failure:
                    raise RuntimeError(f"{name}: {data}")
                return value

            await call("origin_ping", {"show": False})
            await call("origin_new_project", {"show": False})
            await call(
                "origin_import_table", {"path": str(source), "book_name": "Candidate", "sheet_name": "Data"}
            )
            rows = await call(
                "origin_read_worksheet", {"book_name": "Candidate", "sheet_name": "Data", "max_rows": 3}
            )
            report["worksheet_readback"] = rows
            report["checks"]["imported_values"] = rows["total_rows"] == 51 and rows["rows"][0] == {
                "time": 0.0,
                "decay": 2.3,
                "linear": 0.1,
            }
            await call(
                "origin_plot_line",
                {
                    "path": str(source),
                    "x_col": "time",
                    "y_cols": ["decay", "linear"],
                    "graph_name": "CandidatePlot",
                    "title": "Synthetic candidate evaluation",
                    "x_label": "Time (s)",
                    "y_label": "Signal (a.u.)",
                    "export_path": str(directory / "candidate.png"),
                },
            )
            nonlinear = await call(
                "origin_nonlinear_fit_structured",
                {
                    "worksheet": "[Candidate]Data!",
                    "x_col": "time",
                    "y_col": "decay",
                    "function": "ExpDec1",
                    "initial_params": {"y0": 0.2, "A1": 1.8, "t1": 1.0},
                },
                allow_failure=True,
            )
            report["nonlinear"] = nonlinear
            # A true outer ToolResult does not prove native execution or a fit.
            report["checks"]["nonlinear_has_parameters"] = nonlinear.get("executed") is True and bool(
                nonlinear.get("parameters")
            )
            linear = await call(
                "origin_linear_fit",
                {
                    "worksheet": "[Candidate]Data!",
                    "x_col": "time",
                    "y_col": "linear",
                },
            )
            report["linear"] = linear
            coefficients = {item["path"]: item["value"] for item in linear["result"]["parameters"]}
            report["checks"]["linear_coefficients"] = all(
                math.isclose(
                    coefficients[name],
                    expected,
                    rel_tol=0,
                    abs_tol=1e-9,
                )
                for name, expected in {
                    "Parameters.Intercept.Value": 0.1,
                    "Parameters.Slope.Value": 0.2,
                }.items()
            )
            smooth = await call(
                "origin_smooth",
                {
                    "worksheet": "[Candidate]Data!",
                    "x_col": "time",
                    "y_col": "linear",
                    "include_output": True,
                    "output_max_rows": 5,
                },
                allow_failure=True,
            )
            report["checks"]["smoothing_executed"] = smooth.get("executed") is True
            await call(
                "origin_set_cell_value",
                {
                    "book_name": "Candidate",
                    "sheet_name": "Data",
                    "row": 0,
                    "column": "linear",
                    "value": 0.123,
                },
            )
            edited = await call(
                "origin_get_cell_value",
                {
                    "book_name": "Candidate",
                    "sheet_name": "Data",
                    "row": 0,
                    "column": "linear",
                },
            )
            report["checks"]["continuous_cell_edit"] = edited.get("value") == 0.123
            await call("origin_format_graph", {"graph_name": "CandidatePlot", "x_label": "Time (s), edited"})
            await call(
                "origin_create_matrix",
                {
                    "book_name": "CandidateMatrix",
                    "sheet_name": "Values",
                    "data": [[1, 2, 3], [4, 5, 6]],
                },
            )
            matrix = await call(
                "origin_read_matrix",
                {
                    "book_name": "CandidateMatrix",
                    "sheet_name": "Values",
                    "max_rows": 2,
                    "max_cols": 3,
                },
            )
            report["matrix"] = matrix
            report["checks"]["matrix_values"] = matrix.get("data") == [[1, 2, 3], [4, 5, 6]]
            await call("origin_save_project", {"path": str(directory / "candidate.opju")})
            await call("origin_open_project", {"path": str(directory / "candidate.opju")})
            await call("origin_get_worksheet_info", {"book_name": "Candidate", "sheet_name": "Data"})
            reopened = await call(
                "origin_get_cell_value",
                {
                    "book_name": "Candidate",
                    "sheet_name": "Data",
                    "row": 0,
                    "column": "linear",
                },
            )
            report["checks"]["saved_edit_survives_reopen"] = reopened.get("value") == 0.123
            from PIL import Image

            with Image.open(directory / "candidate.png") as picture:
                picture.load()
                report["checks"]["png_decodes"] = picture.width >= 800 and picture.height >= 600
            report["checks"]["project_nonempty"] = (directory / "candidate.opju").stat().st_size > 1024
            report["ok"] = all(report["checks"].values()) and all(
                step["semantic_ok"] for step in report["steps"]
            )
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)[:4000]}
        raise
    finally:
        report["seconds"] = round(time.monotonic() - started, 3)
        write(report_path, report)
    return report["ok"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--candidate-python", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if args.worker:
        worker(directory)
        return
    if not args.candidate_dir or not args.candidate_python:
        parser.error("--candidate-dir and --candidate-python are required")
    args.candidate_dir = args.candidate_dir.resolve()
    args.candidate_python = args.candidate_python.resolve()
    commit = subprocess.check_output(
        ["git", "-C", str(args.candidate_dir), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != PIN:
        raise ValueError(f"Candidate revision differs from reviewed pin: {commit}")
    handshake = directory / "handshake.json"
    if handshake.exists():
        raise ValueError("Use a new output directory; an existing handshake may belong to a live session")
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "CONTROL_PLANE_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GH_TOKEN",
            "GITHUB_TOKEN",
        }
        and not key.startswith("ORIGIN_MCP_")
    }
    env.update(
        {
            "ORIGIN_MCP_BRIDGE_HANDSHAKE": str(handshake),
            "ORIGIN_MCP_BRIDGE_STATUS": str(directory / "status.json"),
            "ORIGIN_MCP_LOG_FILE": str(directory / "bridge.log"),
            "ORIGIN_MCP_ALLOWED_ROOTS": str(directory),
            "ORIGIN_MCP_TOOL_PROFILE": "full",
            "ORIGIN_MCP_BRIDGE_TIMEOUT": "90",
            "PYTHONUTF8": "1",
        }
    )
    with (directory / "worker.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                str(args.candidate_python),
                str(Path(__file__).resolve()),
                "--worker",
                "--output",
                str(directory),
            ],
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 60
            while not handshake.exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Candidate worker failed to start; inspect worker.log")
                time.sleep(0.2)
            ok = asyncio.run(evaluate(args, directory, env))
        finally:
            if handshake.exists() and process.poll() is None:
                with contextlib.suppress(subprocess.TimeoutExpired):
                    subprocess.run(
                        [
                            str(args.candidate_python),
                            "-c",
                            "from origin_mcp.bridge_client import request_bridge; "
                            "request_bridge('shutdown', {'release_origin': True})",
                        ],
                        env=env,
                        stdout=log,
                        stderr=log,
                        timeout=15,
                        check=False,
                    )
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=15)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
                raise RuntimeError(
                    "Candidate worker did not shut down normally; inspect owned Origin process"
                )
    print(json.dumps({"report": str(directory / "candidate-report.json")}), flush=True)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
