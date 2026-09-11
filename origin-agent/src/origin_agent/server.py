"""Eight coarse MCP tools, using the official protocol SDK and compact responses."""

import asyncio
import base64
import json
import time
from typing import Any, Literal

from mcp.server import MCPServer
from mcp_types import CallToolResult, ImageContent, ResourceLink, TextContent, ToolAnnotations

from . import __version__
from .datasets import inspect_dataset
from .discovery import discover
from .jobs import TERMINAL, cancel, get_job, submit
from .models import Workflow
from .native import artifact_path
from .planning import plan_workflow
from .storage import Store, read_json, sha256


def make_server(store: Store | None = None):
    store = store or Store()
    mcp = MCPServer(
        "origin-agent",
        title="Origin Agent Bridge",
        version=__version__,
        instructions="Use inspect → plan → run → get_job(wait_seconds=20). Reuse IDs. "
        "Never invent column units, fitting constraints, preprocessing, or scientific evidence. "
        "Use get_artifact preview to inspect graphs. Completed jobs contain editable native OPJU.",
        log_level="WARNING",
    )
    read = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
    write = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)

    @mcp.tool(annotations=read)
    def origin_status() -> dict[str, Any]:
        """Inspect installation and last native verification without starting Origin."""
        path = store.root / "last-native-engine.json"
        return {
            "plugin_version": __version__,
            **discover(),
            "last_native_engine": read_json(path) if path.exists() else None,
            "data_directories": [str(p) for p in store.allowed_roots],
            "inbox": str(store.root / "inbox"),
            "compute": "local Windows",
            "capabilities": [
                "csv",
                "tsv",
                "xlsx_values",
                "multi_y",
                "error_bars",
                "linear_fit_free_or_zero_intercept",
                "beer_lambert",
                "batch",
                "png",
                "pdf",
                "svg",
                "editable_opju",
                "revision_by_plan",
            ],
            "limits": {"input_mib": 25, "rows": 250000, "columns": 128, "panels_per_job": 12},
        }

    @mcp.tool(annotations=write)
    async def origin_inspect_dataset(path: str, sheet_name: str | None = None) -> dict[str, Any]:
        """Snapshot a local CSV/TSV/XLSX; return column quality and four preview rows. No Origin launch."""
        return await asyncio.to_thread(inspect_dataset, store, path, sheet_name)

    @mcp.tool(annotations=write)
    async def origin_plan_workflow(workflow: Workflow) -> dict[str, Any]:
        """Validate a batch plan without execution. Fit kind, intercept and weighting must be explicit."""
        return await asyncio.to_thread(plan_workflow, store, workflow)

    @mcp.tool(annotations=write)
    async def origin_run_workflow(plan_id: str) -> dict[str, Any]:
        """Queue a validated plan. Repeated calls reuse the same job without rerunning."""
        return await asyncio.to_thread(submit, store, plan_id)

    @mcp.tool(annotations=read)
    async def origin_get_job(job_id: str, wait_seconds: int = 0) -> dict[str, Any]:
        """Get progress/artifacts; wait up to 25 seconds. Terminal results are cached."""
        if not 0 <= wait_seconds <= 25:
            raise ValueError("wait_seconds must be between 0 and 25")
        deadline = time.monotonic() + wait_seconds
        result = await asyncio.to_thread(get_job, store, job_id)
        while result["state"] not in TERMINAL and time.monotonic() < deadline:
            await asyncio.sleep(min(0.5, max(0, deadline - time.monotonic())))
            result = await asyncio.to_thread(get_job, store, job_id, kick=False)
        if "summary" in result:
            result["summary_count"] = len(result["summary"])
            result["summary"] = result["summary"][:12]
            result["artifact_count"] = len(result["artifacts"])
            result["artifacts"] = result["artifacts"][:48]
            result["manifest_artifact_id"] = f"{job_id}/manifest.json"
        return result

    @mcp.tool(annotations=write)
    async def origin_cancel_job(job_id: str) -> dict[str, Any]:
        """Cancel a queued/running job. Only this job's proven owned processes can be terminated."""
        return await asyncio.to_thread(cancel, store, job_id)

    @mcp.tool(annotations=read, structured_output=False)
    async def origin_get_artifact(
        artifact_id: str, mode: Literal["info", "preview", "text"] = "info"
    ) -> CallToolResult:
        """Get a verified artifact link, PNG preview, or bounded JSON/CSV text."""
        path, mime = await asyncio.to_thread(artifact_path, store, artifact_id)
        details = {
            "artifact_id": artifact_id,
            "local_path": str(path),
            "bytes": path.stat().st_size,
            "sha256": await asyncio.to_thread(sha256, path),
            "mime_type": mime,
        }
        content = [
            TextContent(type="text", text=json.dumps(details, ensure_ascii=False)),
            ResourceLink(
                type="resource_link",
                uri=f"origin://artifacts/{artifact_id}",
                name=path.name,
                mime_type=mime,
                size=path.stat().st_size,
            ),
        ]
        if mode == "preview":
            if path.suffix != ".png" or path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("Preview requires a PNG <=8 MiB")
            content.append(
                ImageContent(
                    type="image", data=base64.b64encode(path.read_bytes()).decode(), mime_type="image/png"
                )
            )
        elif mode == "text":
            if path.suffix not in (".json", ".csv") or path.stat().st_size > 128 * 1024:
                raise ValueError(
                    "Text requires JSON/CSV <=128 KiB; use the artifact resource for larger files"
                )
            content.append(TextContent(type="text", text=path.read_text(encoding="utf-8")))
        return CallToolResult(content=content)

    @mcp.tool(annotations=read)
    async def origin_inspect_project(job_id: str) -> dict[str, Any]:
        """Read a verified OPJU index/workflow. Edit this workflow to create a revision."""
        path, _ = await asyncio.to_thread(artifact_path, store, f"{job_id}/manifest.json")
        manifest = read_json(path)
        return {key: manifest[key] for key in ("engine", "workflow", "project_index", "verification")}

    @mcp.resource("origin://artifacts/{job_id}/{name}")
    async def artifact(job_id: str, name: str) -> bytes:
        path, _ = await asyncio.to_thread(artifact_path, store, f"{job_id}/{name}")
        if path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("MCP binary transfer limit is 32 MiB; use the local artifact path")
        return await asyncio.to_thread(path.read_bytes)

    return mcp
