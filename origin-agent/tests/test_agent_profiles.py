import json

import pytest
from mcp import Client

from origin_agent import jobs
from origin_agent.agent_profiles import PRESETS, configure_profile, parse_arguments, resolve_profile
from origin_agent.planning import load_plan
from origin_agent.server import make_server
from origin_agent.storage import write_json


@pytest.mark.anyio
async def test_economy_reduces_inventory_and_exposes_every_operation(store):
    full = make_server(store, profile="full")
    compact = make_server(store, profile="economy")
    original = await full.list_tools()
    advertised = await compact.list_tools()
    size = lambda items: len(json.dumps([t.model_dump(mode="json") for t in items]).encode())  # noqa: E731
    assert len(advertised) == 5
    assert size(advertised) < size(original) * 0.4
    async with Client(compact) as client:
        catalog = (await client.call_tool("origin_help", {})).structured_content
        assert {o["name"] for o in catalog["operations"]} == {t.name for t in original}
        for tool in original:
            detail = await client.call_tool("origin_help", {"operation": tool.name})
            assert detail.structured_content["input_schema"] == tool.input_schema
        assert next(t for t in advertised if t.name == "origin_call").annotations.destructive_hint


@pytest.mark.anyio
@pytest.mark.parametrize("preset", list(PRESETS))
async def test_each_preset_uses_same_guarded_engine(store, dataset, preset):
    async with Client(make_server(store, profile="economy", preset=preset)) as client:
        status = await client.call_tool("origin_status", {})
        assert status.structured_content["agent_profile"]["preset"] == preset
        bad = await client.call_tool(
            "origin_call",
            {
                "operation": "origin_plan_workflow",
                "arguments_json": '{"workflow":{"python":"1+1"}}',
            },
        )
        assert bad.is_error
        unknown = await client.call_tool("origin_call", {"operation": "exec", "arguments_json": "{}"})
        assert unknown.is_error
        plan = await client.call_tool(
            "origin_recipe",
            {
                "dataset_id": dataset["dataset_id"],
                "x": "Concentration",
                "y": ["Absorbance"],
            },
        )
        assert not plan.is_error
        assert (
            load_plan(store, plan.structured_content["plan_id"])["workflow"]["panels"][0]["analysis"] is None
        )


@pytest.mark.anyio
async def test_recipe_requires_assumptions_reuses_jobs_and_matches_full_plan(store, dataset, monkeypatch):
    monkeypatch.setattr(jobs, "spawn", lambda *a, **k: None)
    args = {
        "dataset_id": dataset["dataset_id"],
        "x": "Concentration",
        "y": ["Absorbance"],
        "recipe": "linear_fit",
        "action": "run",
    }
    async with Client(make_server(store, profile="economy")) as client:
        assert (await client.call_tool("origin_recipe", args)).is_error
        with jobs.database(store) as db:
            assert db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 0
        args.update(intercept="free", weighting="none")
        first = await client.call_tool("origin_recipe", args)
        second = await client.call_tool("origin_recipe", args)
        assert not first.is_error
        assert first.structured_content["job_id"] == second.structured_content["job_id"]
        plan = load_plan(store, first.structured_content["plan_id"])
        same = await client.call_tool(
            "origin_call",
            {
                "operation": "origin_plan_workflow",
                "arguments_json": json.dumps({"workflow": plan["workflow"]}),
            },
        )
        assert same.structured_content["plan_id"] == first.structured_content["plan_id"]
        invalid = {**args, "y": ["Invented column"]}
        assert (await client.call_tool("origin_recipe", invalid)).is_error


@pytest.mark.parametrize(
    "value", ["[]", '{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e400}', "```{}", "{"]
)
def test_malformed_or_ambiguous_json_rejected(value):
    with pytest.raises(ValueError):
        parse_arguments(value)


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["full", "economy"])
async def test_text_only_profile_blocks_images_and_visual_input(store, mode):
    async with Client(make_server(store, profile=mode, vision="off")) as client:
        image = await client.call_tool(
            "origin_get_artifact", {"artifact_id": "irrelevant", "mode": "preview"}
        )
        assert image.is_error
        assert "Vision is off" in str(image)
        args = {
            "session_id": "a" * 32,
            "request_id": "one",
            "expected_revision": 1,
            "gui": {
                "action": "click",
                "observation_id": "b" * 32,
                "target_id": "window:test",
                "position": {"x": 0.5, "y": 0.5},
            },
        }
        result = (
            await client.call_tool("origin_gui", args)
            if mode == "full"
            else await client.call_tool(
                "origin_call",
                {"operation": "origin_gui", "arguments_json": json.dumps(args)},
            )
        )
        assert result.is_error
        assert "Vision is off" in str(result)


def test_profile_precedence_and_recovery_copy(store, monkeypatch):
    configure_profile(store, "deepseek", "economy", "off")
    assert resolve_profile(store).preset == "deepseek"
    monkeypatch.setenv("ORIGIN_AGENT_PROFILE", "full")
    assert resolve_profile(store).mode == "full"
    assert resolve_profile(store, mode="economy").mode == "economy"
    configure_profile(store, "gpt-terra", "economy", "auto")
    previous = json.loads((store.root / "agent-profile.previous.json").read_text())
    assert previous["preset"] == "deepseek"
    write_json(store.root / "agent-profile.json", {"mode": "unknown"})
    with pytest.raises(ValueError):
        resolve_profile(store, mode="unknown")


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["full", "economy"])
async def test_correctable_errors_are_bounded_without_echoing_inputs(store, mode):
    async with Client(make_server(store, profile=mode)) as client:

        async def call(name, arguments):
            if mode == "full":
                return await client.call_tool(name, arguments)
            return await client.call_tool(
                "origin_call",
                {
                    "operation": name,
                    "arguments_json": json.dumps(arguments),
                },
            )

        invalid = await call("origin_plan_workflow", {"workflow": {"private": "do-not-echo-this" * 2000}})
        assert invalid.is_error
        message = str(invalid.content)
        assert "do-not-echo-this" not in message
        assert "panels" in message and len(message) < 1800
        syntax = await call(
            "origin_run_program",
            {
                "program": {
                    "title": "invalid syntax",
                    "language": "python",
                    "code": "def incomplete(",
                }
            },
        )
        assert syntax.is_error
        assert '"line": 1' in syntax.content[0].text


@pytest.mark.anyio
async def test_economy_accepts_cached_full_names_with_same_validation(store, dataset, tmp_path):
    async with Client(make_server(store, profile="economy", vision="off")) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert "origin_inspect_dataset" not in names and len(names) == 5
        inspected = await client.call_tool(
            "origin_inspect_dataset", {"path": str(tmp_path / "calibration.csv")}
        )
        assert not inspected.is_error
        assert inspected.structured_content["sha256"] == dataset["sha256"]
        assert inspected.structured_content["columns"] == dataset["columns"]
        args = {
            "workflow": {
                "panels": [{"dataset_id": dataset["dataset_id"], "x": "Concentration", "y": ["Absorbance"]}]
            }
        }
        direct = await client.call_tool("origin_plan_workflow", args)
        wrapped = await client.call_tool(
            "origin_call", {"operation": "origin_plan_workflow", "arguments_json": json.dumps(args)}
        )
        assert not direct.is_error and not wrapped.is_error
        assert direct.structured_content["plan_id"] == wrapped.structured_content["plan_id"]
        invalid = await client.call_tool("origin_plan_workflow", {"workflow": {"private": "do-not-echo"}})
        assert invalid.is_error and "do-not-echo" not in str(invalid.content)
        assert "validation" in str(invalid.content)
        assert (await client.call_tool("exec", {})).is_error
        image = await client.call_tool("origin_get_artifact", {"artifact_id": "invalid", "mode": "preview"})
        assert image.is_error and "Vision is off" in str(image.content)
        gui = await client.call_tool(
            "origin_gui",
            {
                "session_id": "a" * 32,
                "expected_revision": 1,
                "request_id": "cached",
                "gui": {
                    "action": "click",
                    "observation_id": "b" * 32,
                    "target_id": "window:test",
                    "position": {"x": 0.5, "y": 0.5},
                },
            },
        )
        assert gui.is_error and "Vision is off" in str(gui.content)
        assert {t.name for t in (await client.list_tools()).tools} == names
