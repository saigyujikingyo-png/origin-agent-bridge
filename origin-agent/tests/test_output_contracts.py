"""Public output contracts: discovery, strict validation, recovery and media compatibility."""

import json
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from mcp import Client
from mcp_types import CallToolResult, TextContent
from PIL import Image

from origin_agent.jobs import database
from origin_agent.output_contracts import bounded_json, output_schema, validate_result
from origin_agent.server import make_server
from origin_agent.storage import sha256, write_json


def contains_required(schema):
    if isinstance(schema, dict):
        return bool(schema.get("required")) or any(contains_required(v) for v in schema.values())
    return isinstance(schema, list) and any(contains_required(v) for v in schema)


@pytest.mark.anyio
@pytest.mark.parametrize("profile", ["full", "economy"])
async def test_all_public_tools_declare_meaningful_output_schemas(store, profile):
    async with Client(make_server(store, profile=profile)) as client:
        for tool in (await client.list_tools()).tools:
            assert tool.output_schema and tool.output_schema.get("type") == "object", tool.name
            assert contains_required(tool.output_schema), tool.name
        result = await client.call_tool("origin_status", {})
        assert not result.is_error
        assert result.structured_content["output_contract"]["version"] == "1.0.0"
        assert json.loads(result.content[0].text) == result.structured_content


@pytest.mark.anyio
async def test_operation_help_exposes_the_matching_result_schema(store):
    full = make_server(store, profile="full")
    async with Client(make_server(store, profile="economy")) as client:
        for tool in await full.list_tools():
            result = await client.call_tool("origin_help", {"operation": tool.name})
            assert not result.is_error
            assert result.structured_content["output_schema"] == tool.output_schema
            assert result.structured_content["output_contract_version"] == "1.0.0"


def assert_contract(operation, result):
    assert result.structured_content is not None
    Draft202012Validator(output_schema(operation)).validate(result.structured_content)
    assert json.loads(result.content[0].text) == result.structured_content
    assert result.meta["origin_output_contract_version"] == "1.0.0"
    return result.structured_content


def wrapped(payload, **kwargs):
    return CallToolResult(
        content=[TextContent(text="outdated fallback")], structured_content=payload, **kwargs
    )


@pytest.mark.anyio
async def test_schemas_are_valid_and_compact_at_protocol_boundary(store):
    sizes = {}
    for profile in ("full", "economy"):
        async with Client(make_server(store, profile=profile)) as client:
            tools = (await client.list_tools()).tools
            for tool in tools:
                Draft202012Validator.check_schema(tool.output_schema)
            sizes[profile] = len(json.dumps([t.model_dump(mode="json") for t in tools]).encode())
    assert sizes["full"] < 200_000
    assert sizes["economy"] < 40_000
    assert sizes["economy"] < sizes["full"] * 0.25


@pytest.mark.anyio
@pytest.mark.parametrize("profile", ["full", "economy"])
async def test_live_read_plan_and_error_routes_conform(store, profile):
    async with Client(make_server(store, profile=profile)) as client:

        async def call(operation, args):
            tool = "origin_call" if profile == "economy" else operation
            arguments = (
                {"operation": operation, "arguments_json": json.dumps(args)} if profile == "economy" else args
            )
            result = await client.call_tool(tool, arguments)
            assert_contract(tool, result)
            assert_contract(operation, result)
            return result

        imported = await call("origin_import_table", {"content": "X,Y\n0,1\n1,3\n2,5\n", "format": "csv"})
        assert not imported.is_error
        data = imported.structured_content
        assert data["row_count"] == 3 and data["sheet_name"] is None
        workflow = {"panels": [{"dataset_id": data["dataset_id"], "x": "X", "y": ["Y"]}]}
        plan = await call("origin_plan_workflow", {"workflow": workflow})
        assert not plan.is_error and plan.structured_content["native_execution"] is False
        invalid = await call("origin_plan_workflow", {"workflow": {"panels": []}})
        assert invalid.is_error and invalid.structured_content["error"] == "validation"
        missing = await call("origin_get_job", {"job_id": "f" * 32})
        assert missing.is_error and missing.structured_content["error"] == "invalid_request"
        coverage = await call("origin_capabilities", {"query": "coverage"})
        assert not coverage.is_error
        if profile == "economy":
            for args in ({}, {"operation": "origin_get_artifact", "query": "receiver"}):
                help_result = await client.call_tool("origin_help", args)
                assert_contract("origin_help", help_result)
                assert not help_result.is_error


def manifest_fixture(store, state="succeeded"):
    job, plan = "a" * 32, "b" * 32
    folder = store.path("jobs", job)
    folder.mkdir(exist_ok=True)
    with database(store) as db:
        db.execute(
            "INSERT INTO jobs (id,plan_id,state,created,updated,error) VALUES (?,?,?,?,?,?)",
            (job, plan, state, 0.0, 1.0, "cancelled" if state == "cancelled" else None),
        )
    verification = {
        "vendor_native": True,
        "project_reopened": True,
        "data_roundtrip": True,
        "graphs_reopened": 1,
        "native_reports_reopened": 0,
        "png_decoded": False,
        "visual_review": "not performed",
        "seconds": 0.1,
    }
    manifest = {
        "summary": [{"panels": 1, "analysis": "plot only"}],
        "verification": verification,
        "artifacts": [],
    }
    write_json(folder / "manifest.json", manifest)
    return job, folder, manifest


@pytest.mark.anyio
@pytest.mark.parametrize("state", ["queued", "running", "succeeded", "failed", "cancelled", "interrupted"])
@pytest.mark.parametrize("profile", ["full", "economy"])
async def test_all_job_states_preserve_semantics(store, monkeypatch, state, profile):
    # Exercise the queue reader, not hand-authored final tool responses. Prevent a native worker start.
    monkeypatch.setattr("origin_agent.jobs._kick_locked", lambda store: None)
    job, folder, _ = manifest_fixture(store, state)
    write_json(
        folder / "progress.json",
        {"stage": "connected", "completed_panels": 0, "total_panels": 3, "elapsed_seconds": 0.1},
    )
    if state == "failed":
        write_json(folder / "error.json", {"type": "ModuleNotFoundError", "labtalk_output": ""})
    async with Client(make_server(store, profile=profile)) as client:
        for operation in ("origin_get_job", "origin_cancel_job"):
            args = {"job_id": job}
            result = await client.call_tool(
                "origin_call" if profile == "economy" else operation,
                {"operation": operation, "arguments_json": json.dumps(args)}
                if profile == "economy"
                else args,
            )
            assert not result.is_error, result
            data = assert_contract(operation, result)
            if operation == "origin_get_job":
                assert data["state"] == state
                assert data["terminal"] is (state not in ("queued", "running"))
                if state == "succeeded":
                    assert data["verification"]["png_decoded"] is False
                    assert data["verification"]["native_reports_reopened"] == 0
                    assert "graph_text_roundtrip" not in data["verification"]
                elif data["terminal"]:
                    assert "next_action" in data and "poll_after_seconds" not in data
                else:
                    assert "summary" not in data and "poll_after_seconds" in data
                if state == "failed":
                    assert data["recovery"]["kind"] == "missing_python_dependency"


@pytest.mark.anyio
async def test_invalid_post_submit_output_retains_identity_without_retry(store, monkeypatch):
    calls = []

    def submit_once(store, plan_id, **kwargs):
        calls.append(plan_id)
        return {
            "job_id": "c" * 32,
            "plan_id": plan_id,
            "state": "unrecognized",
            "private_payload": "do not expose",
        }

    monkeypatch.setattr("origin_agent.server.submit", submit_once)
    async with Client(make_server(store, profile="economy")) as client:
        result = await client.call_tool(
            "origin_call",
            {"operation": "origin_run_workflow", "arguments_json": json.dumps({"plan_id": "d" * 32})},
        )
    data = assert_contract("origin_call", result)
    assert result.is_error and data["error"] == "output_validation"
    assert data["job_id"] == "c" * 32 and data["plan_id"] == "d" * 32
    assert data["recovery"]["arguments"]["job_id"] == data["job_id"]
    assert calls == ["d" * 32]
    assert "do not expose" not in str(result)


@pytest.mark.anyio
async def test_unexpected_exception_is_structured_and_sanitized(store, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("sensitive backend details")

    monkeypatch.setattr("origin_agent.server.discover", broken)
    async with Client(make_server(store)) as client:
        result = await client.call_tool("origin_status", {})
    assert result.is_error and assert_contract("origin_status", result)["error"] == "execution"
    assert "sensitive backend details" not in str(result)


@pytest.mark.parametrize(
    "change",
    [
        {"terminal": "false"},
        {"terminal": 0},
        {"elapsed_seconds": float("nan")},
        {"state": "complete"},
        {"job_id": "../private"},
        {"elapsed_seconds": -1},
    ],
)
def test_malformed_lifecycle_never_becomes_success(change):
    payload = {
        "job_id": "a" * 32,
        "plan_id": "b" * 32,
        "state": "queued",
        "terminal": False,
        "error": None,
        "cancel_requested": False,
        "elapsed_seconds": 0.0,
        "poll_after_seconds": 3,
    }
    payload.update(change)
    result = validate_result("origin_get_job", wrapped(payload))
    assert result.is_error and assert_contract("origin_get_job", result)["error"] == "output_validation"


@pytest.mark.parametrize("payload", [float("inf"), {"bad": {1: "x"}}, {"bad": (1, 2)}, ["x"] * 65537])
def test_non_json_or_unbounded_payload_rejected(payload):
    with pytest.raises(ValueError):
        bounded_json(payload)


def test_cyclic_output_rejected():
    payload = {}
    payload["loop"] = payload
    with pytest.raises(ValueError):
        bounded_json(payload)


@pytest.mark.anyio
@pytest.mark.parametrize("profile", ["full", "economy"])
async def test_all_artifact_modes_match_metadata_and_keep_content_positions(store, profile):
    job, folder, manifest = manifest_fixture(store)
    Image.new("RGB", (20, 15), "blue").save(folder / "plot.png")
    text = "Concentration,Absorbance\n" + "0.00001,0.012\n" * 100
    (folder / "result.csv").write_text(text, encoding="utf-8", newline="")
    (folder / "project.opju").write_bytes(bytes(range(256)))
    for name, mime in [
        ("plot.png", "image/png"),
        ("result.csv", "text/csv"),
        ("project.opju", "application/octet-stream"),
    ]:
        path = folder / name
        manifest["artifacts"].append(
            {"name": name, "mime_type": mime, "sha256": sha256(path), "bytes": path.stat().st_size}
        )
    write_json(folder / "manifest.json", manifest)
    async with Client(make_server(store, profile=profile, vision="on")) as client:
        for mode, filename in [("info", "plot.png"), ("preview", "plot.png"), ("download", "project.opju")]:
            result = await client.call_tool(
                "origin_get_artifact", {"artifact_id": f"{job}/{filename}", "mode": mode}
            )
            assert not result.is_error, result
            data = assert_contract("origin_get_artifact", result)
            assert data["mode"] == mode and data["sha256"] == sha256(folder / filename)
            assert result.content[1].type == "resource_link"
            if mode == "info":
                assert len(result.content) == 2 and "content_index" not in data
            else:
                assert data["content_index"] == 2 and len(result.content) == 3
                assert result.content[2].type == ("image" if mode == "preview" else "resource")
            assert len(json.dumps(data)) < 1000
        offset, pieces = 0, []
        while offset is not None:
            result = await client.call_tool(
                "origin_get_artifact",
                {"artifact_id": f"{job}/result.csv", "mode": "text", "offset": offset, "max_chars": 256},
            )
            data = assert_contract("origin_get_artifact", result)
            page = json.loads(result.content[2].text)
            assert data["pagination"] == {k: v for k, v in page.items() if k != "text"}
            pieces.append(page["text"])
            offset = data["pagination"]["next_offset"]
        assert "".join(pieces) == text


def test_error_flag_is_enforced_and_schema_copy_is_isolated():
    result = validate_result("origin_status", wrapped({"error": "execution", "message": "failed"}))
    assert result.is_error and result.structured_content["error"] == "output_validation"
    schema = output_schema("origin_get_job")
    schema.clear()
    assert output_schema("origin_get_job")["type"] == "object"


def test_boolean_native_evidence_cannot_be_an_integer():
    payload = {
        "job_id": "a" * 32,
        "plan_id": "b" * 32,
        "state": "succeeded",
        "terminal": True,
        "error": None,
        "cancel_requested": False,
        "elapsed_seconds": 0.1,
        "summary": [{"panels": 1, "analysis": "plot only"}],
        "artifacts": [],
        "verification": {
            "vendor_native": True,
            "project_reopened": True,
            "data_roundtrip": True,
            "graphs_reopened": 1,
            "native_reports_reopened": 0,
            "png_decoded": False,
            "visual_review": "not performed",
            "seconds": 0.1,
        },
    }
    valid = validate_result("origin_get_job", wrapped(payload))
    assert not valid.is_error
    corrupt = deepcopy(payload)
    corrupt["verification"]["vendor_native"] = 1
    assert validate_result("origin_get_job", wrapped(corrupt)).is_error


@pytest.mark.anyio
@pytest.mark.parametrize(
    "state", ["opening", "executing", "ready", "gui", "suspended", "closed", "needs_attention"]
)
async def test_session_state_survives_direct_and_dispatch_routes(store, state):
    from origin_agent.sessions import session_path

    session_id = "e" * 32
    state_data = {
        "session_id": session_id,
        "title": "Fixture session",
        "revision": 2,
        "visible": False,
        "state": state,
        "active_job": None,
        "gui_transaction": None,
        "project_index": {"pages": [], "graphs": []},
        "worker_token": "never exported",
    }
    path = session_path(store, session_id)
    path.parent.mkdir()
    write_json(path, state_data)
    async with Client(make_server(store, profile="economy")) as client:
        args = {"action": "inspect", "session_id": session_id}
        direct = await client.call_tool("origin_session", args)
        dispatched = await client.call_tool(
            "origin_call", {"operation": "origin_session", "arguments_json": json.dumps(args)}
        )
    assert not direct.is_error and not dispatched.is_error
    assert assert_contract("origin_session", direct) == assert_contract("origin_call", dispatched)
    assert direct.structured_content["state"] == state
    assert "never exported" not in str(direct)


def test_missing_media_block_cannot_be_advertised_as_delivered():
    payload = {
        "artifact_id": "a" * 32 + "/plot.png",
        "local_path": "plot.png",
        "bytes": 10,
        "sha256": "b" * 64,
        "mime_type": "image/png",
        "mode": "preview",
        "content_index": 2,
    }
    result = validate_result("origin_get_artifact", wrapped(payload))
    assert result.is_error and assert_contract("origin_get_artifact", result)["error"] == "output_validation"
