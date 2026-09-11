import concurrent.futures
import json
import time

import pytest
from mcp import Client

from origin_agent import datasets, jobs
from origin_agent.datasets import dataset_table, import_table
from origin_agent.models import Workflow
from origin_agent.planning import load_plan, plan_workflow
from origin_agent.programs import OriginProgram, prepare_program
from origin_agent.server import make_server
from origin_agent.storage import write_json

CSV = "Concentration,Absorbance\n0.00002,0.116\n0.00004,0.212\n0.00008,0.404\n0.00012,0.596\n"


def test_cloud_table_replay_and_concurrent_calls_reuse_immutable_snapshot(store):
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: import_table(store, CSV), range(4)))
    assert len({value["dataset_id"] for value in results}) == 1
    dataset_id = results[0]["dataset_id"]
    meta, columns, rows = dataset_table(store, dataset_id)
    assert columns == ["Concentration", "Absorbance"]
    assert rows[-1] == ["0.00012", "0.596"]
    assert meta["row_count"] == 4
    assert len(list((store.root / "datasets").iterdir())) == 1
    (store.path("datasets", dataset_id) / "source.csv").write_text("tampered")
    with pytest.raises(ValueError, match="integrity"):
        import_table(store, CSV)


def test_cloud_tsv_unicode_and_exact_content_identity(store):
    text = "浓度\t吸光度\n1\t0.1\n2\t0.2\n3\t0.3\n4\t0.4\n5\t0.5\n"
    first = import_table(store, text, "tsv")
    second = import_table(store, text.replace("0.5", "0.6"), "tsv")
    assert first["dataset_id"] != second["dataset_id"]
    assert first["preview_columns"] == ["浓度", "吸光度"]
    assert len(first["preview"]) == 4
    assert dataset_table(store, first["dataset_id"])[2][-1] == ["5", "0.5"]


@pytest.mark.parametrize("content", ["", "X,X\n1,2\n", "X,Y\n1\n", "X,Y\n"])
def test_invalid_cloud_table_never_becomes_a_dataset(store, content):
    with pytest.raises(ValueError):
        import_table(store, content)
    assert list((store.root / "datasets").iterdir()) == []


def test_cloud_table_byte_limit_and_numeric_validation(store, monkeypatch):
    monkeypatch.setattr(datasets, "MAX_BYTES", 16)
    with pytest.raises(ValueError, match="25 MiB"):
        import_table(store, "浓度,吸光度\n1,2\n")
    monkeypatch.setattr(datasets, "MAX_BYTES", 1024)
    item = import_table(store, "X,Y\n1,2\n2,nan\n3,6\n")
    spec = Workflow.model_validate({"panels": [{"dataset_id": item["dataset_id"], "x": "X", "y": ["Y"]}]})
    with pytest.raises(ValueError, match="No rows dropped"):
        plan_workflow(store, spec)


@pytest.mark.anyio
async def test_cloud_beer_recipe_works_through_cached_economy_dispatch(store, monkeypatch):
    monkeypatch.setattr(jobs, "spawn", lambda *a, **k: None)
    async with Client(make_server(store, profile="economy")) as client:

        async def call(operation, args):
            return await client.call_tool(
                "origin_call", {"operation": operation, "arguments_json": json.dumps(args)}
            )

        info = (
            await client.call_tool("origin_help", {"operation": "origin_import_table"})
        ).structured_content
        assert info["input_schema"]["properties"]["format"]["enum"] == ["csv", "tsv"]
        imported = await call("origin_import_table", {"content": CSV})
        assert not imported.is_error
        args = {
            "dataset_id": imported.structured_content["dataset_id"],
            "x": "Concentration",
            "y": ["Absorbance"],
            "recipe": "beer_lambert",
            "action": "run",
            "intercept": "free",
            "weighting": "none",
            "unknown_absorbance": 0.366,
            "path_length_cm": 1,
            "concentration_scale_molar": 1,
        }
        first = await call("origin_recipe", args)
        second = await call("origin_recipe", args)
        assert not first.is_error
        assert first.structured_content["job_id"] == second.structured_content["job_id"]
        plan = load_plan(store, first.structured_content["plan_id"])
        assert plan["workflow"]["panels"][0]["analysis"] == {
            "kind": "beer_lambert",
            "intercept": "free",
            "weighting": "none",
            "unknown_absorbance": 0.366,
            "path_length_cm": 1,
            "concentration_scale_molar": 1,
        }
        assert len((await client.list_tools()).tools) == 5
        for change in (
            {"intercept": "unspecified"},
            {"weighting": "unspecified"},
            {"concentration_scale_molar": None},
            {"recipe": "linear_fit"},
            {"recipe": "plot"},
        ):
            assert (await call("origin_recipe", {**args, **change})).is_error


@pytest.mark.parametrize(
    "state,error_type",
    [
        ("failed", "ModuleNotFoundError"),
        ("failed", "AttributeError"),
        ("cancelled", "RuntimeError"),
        ("interrupted", "RuntimeError"),
    ],
)
def test_terminal_jobs_stop_polling_and_explain_last_stage(store, monkeypatch, state, error_type):
    monkeypatch.setattr(jobs, "spawn", lambda *a, **k: None)
    plan = prepare_program(store, OriginProgram(title="Synthetic failure", language="python", code="pass"))
    pending = jobs.submit(store, plan["plan_id"], expected_kind="program")
    assert pending["terminal"] is False and pending["poll_after_seconds"] > 0
    directory = store.path("jobs", pending["job_id"])
    write_json(directory / "progress.json", {"stage": "executing_program", "origin_pid": 123})
    write_json(directory / "error.json", {"type": error_type, "message": "synthetic error"})
    with jobs.database(store) as db:
        db.execute(
            "UPDATE jobs SET state=?,updated=?,error=? WHERE id=?",
            (state, time.time(), "synthetic error", pending["job_id"]),
        )
    done = jobs.get_job(store, pending["job_id"], kick=False)
    assert done["terminal"] is True
    assert "poll_after_seconds" not in done
    assert "Stop polling" in done["next_action"]
    assert done["progress"]["stage"] == state
    assert done["progress"]["last_stage"] == "executing_program"
    assert "origin_pid" not in done["progress"]
    assert done["elapsed_seconds"] >= 0
    if error_type == "ModuleNotFoundError":
        assert done["recovery"]["kind"] == "missing_python_dependency"
    elif error_type == "AttributeError":
        assert "label('xb').text" in done["recovery"]["instruction"]
