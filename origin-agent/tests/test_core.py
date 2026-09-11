import concurrent.futures
import json

import pytest
from pydantic import ValidationError

from origin_agent import jobs
from origin_agent.datasets import dataset_table, inspect_dataset
from origin_agent.models import Workflow
from origin_agent.native import reference_fit
from origin_agent.planning import load_plan, plan_workflow
from origin_agent.storage import BusyError, file_lock, read_json, write_json


def workflow(dataset, **extra):
    return Workflow.model_validate(
        {
            "panels": [
                {"dataset_id": dataset["dataset_id"], "x": "Concentration", "y": ["Absorbance"], **extra}
            ]
        }
    )


def test_fit_assumptions_required(dataset):
    with pytest.raises(ValidationError):
        workflow(dataset, analysis={"kind": "linear_fit"})
    with pytest.raises(ValidationError):
        workflow(
            dataset,
            analysis={"kind": "linear_fit", "intercept": "free", "weighting": "none", "python": "print('x')"},
        )


def test_plan_is_deterministic_and_detects_tampering(store, dataset):
    spec = workflow(dataset)
    one = plan_workflow(store, spec)
    assert one == plan_workflow(store, spec)
    path = store.path("plans", one["plan_id"]) / "plan.json"
    altered = read_json(path)
    altered["workflow"]["panels"][0]["y"] = ["Replicate"]
    write_json(path, altered)
    with pytest.raises(ValueError, match="integrity"):
        load_plan(store, one["plan_id"])


@pytest.mark.parametrize("value", ["", "nan", "inf", "mistyped"])
def test_invalid_numeric_rows_never_silently_dropped(store, tmp_path, value):
    source = tmp_path / "bad.csv"
    source.write_text(f"Concentration,Absorbance\n0,1\n1,{value}\n2,3\n", encoding="utf-8")
    meta = inspect_dataset(store, str(source))
    with pytest.raises(ValueError, match="No rows dropped"):
        plan_workflow(store, workflow(meta))


def test_snapshot_survives_source_change_and_detects_snapshot_change(store, dataset, tmp_path):
    (tmp_path / "calibration.csv").write_text("changed", encoding="utf-8")
    assert len(dataset_table(store, dataset["dataset_id"])[2]) == 5
    source = store.path("datasets", dataset["dataset_id"]) / "source.csv"
    source.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        dataset_table(store, dataset["dataset_id"])


def test_reject_paths_outside_roots(store, tmp_path):
    path = tmp_path.parent / "outside.csv"
    path.write_text("x,y\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="configured"):
        inspect_dataset(store, str(path))
    with pytest.raises(ValueError):
        store.path("jobs", "../outside")


def test_xlsx_select_sheet_and_reject_formula(store, tmp_path):
    import openpyxl

    book = openpyxl.Workbook()
    book.active.append(["x", "y"])
    book.active.append([1, "=1+2"])
    book.create_sheet("Second")
    path = tmp_path / "formula.xlsx"
    book.save(path)
    with pytest.raises(ValueError, match="sheet_name"):
        inspect_dataset(store, str(path))
    with pytest.raises(ValueError, match="formulas"):
        inspect_dataset(store, str(path), "Sheet")


def test_independent_oracle_known_solution():
    x, y = [0.0, 1.0, 2.0, 3.0, 4.0], [1.1, 2.9, 5.0, 7.1, 8.9]
    assert reference_fit(x, y, "free") == pytest.approx((1.98, 1.04, 0.036))
    assert reference_fit([1.0, 2.0, 3.0], [2.0, 4.0, 6.0], "zero") == pytest.approx((2.0, 0.0, 0.0))


def test_concurrent_submit_reuses_job_and_cancel_is_terminal(store, dataset, monkeypatch):
    monkeypatch.setattr(jobs, "spawn", lambda *args, **kwargs: None)
    plan = plan_workflow(store, workflow(dataset))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        answers = list(pool.map(lambda _: jobs.submit(store, plan["plan_id"]), range(8)))
    assert len({a["job_id"] for a in answers}) == 1
    job_id = answers[0]["job_id"]
    assert jobs.cancel(store, job_id)["state"] == "cancelled"
    assert jobs.submit(store, plan["plan_id"])["state"] == "cancelled"


def test_lock_enforces_device_serialization(tmp_path):
    path = tmp_path / "lock"
    with file_lock(path):
        with pytest.raises(BusyError):
            with file_lock(path, timeout=0):
                pytest.fail("lock is not exclusive")
    with file_lock(path, timeout=0):
        pass


def test_input_and_summary_are_small(store, dataset):
    plan = plan_workflow(store, workflow(dataset))
    assert len(json.dumps(dataset)) < 4000
    assert len(json.dumps(plan)) < 2500


def test_atomic_write_retries_transient_windows_share_violation(tmp_path, monkeypatch):
    import os

    original = os.replace
    calls = []

    def flaky(source, target):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError("transient read handle")
        return original(source, target)

    monkeypatch.setattr(os, "replace", flaky)
    path = tmp_path / "progress.json"
    write_json(path, {"stage": "verified"})
    assert read_json(path) == {"stage": "verified"}
    assert len(calls) == 3
