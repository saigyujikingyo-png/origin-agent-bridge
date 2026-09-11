import hashlib

from . import __version__
from .datasets import dataset_table, numeric_columns
from .models import Workflow
from .storage import Store, json_bytes, read_json, write_json


def plan_workflow(store: Store, workflow: Workflow) -> dict:
    sources, summaries, tables = {}, [], {}
    for panel in workflow.panels:
        if panel.dataset_id not in tables:
            tables[panel.dataset_id] = dataset_table(store, panel.dataset_id)
        meta, headers, rows = tables[panel.dataset_id]
        selected = numeric_columns(headers, rows, [panel.x, *panel.y, *panel.y_errors.values()])
        if any(value < 0 for name in panel.y_errors.values() for value in selected[name]):
            raise ValueError("Error-bar magnitudes must be nonnegative")
        if panel.analysis:
            x = selected[panel.x]
            if len(x) < 3 or len(set(x)) < 2:
                raise ValueError("Linear fitting requires at least 3 rows and 2 distinct X values")
            for y in panel.y:
                if len(set(selected[y])) < 2:
                    raise ValueError("Constant Y cannot produce an interpretable R-squared; inspect the data")
        sources[panel.dataset_id] = {"sha256": meta["sha256"], "name": meta["name"], "rows": len(rows)}
        summaries.append(
            {
                "title": panel.title,
                "rows": len(rows),
                "x": panel.x,
                "y": panel.y,
                "analysis": panel.analysis.model_dump() if panel.analysis else None,
                "error_bars": panel.y_errors,
                "style": panel.style.model_dump(),
            }
        )
    spec = workflow.model_dump()
    payload = {"schema_version": 1, "engine_version": __version__, "workflow": spec, "sources": sources}
    fingerprint = hashlib.sha256(json_bytes(payload)).hexdigest()
    identifier = fingerprint[:32]
    directory = store.path("plans", identifier)
    directory.mkdir(exist_ok=True)
    assumptions = ["No rows dropped, no smoothing, no baseline subtraction"]
    if any(panel.y_errors for panel in workflow.panels):
        assumptions.append("Error bars are displayed for the explicitly mapped Y columns")
    if any(panel.analysis for panel in workflow.panels):
        assumptions.append("All requested regressions use explicitly unweighted fitting")
    result = {
        **payload,
        "plan_id": identifier,
        "sha256": fingerprint,
        "summary": summaries,
        "outputs": ["project.opju", "manifest.json", *workflow.formats],
        "assumptions": assumptions,
        "native_execution": False,
    }
    write_json(directory / "plan.json", result)
    return {
        key: result[key]
        for key in ("plan_id", "sha256", "summary", "outputs", "assumptions", "native_execution")
    }


def load_plan(store: Store, identifier: str):
    plan = read_json(store.path("plans", identifier) / "plan.json")
    if plan.get("kind") == "session":
        from .sessions import load_session_plan

        return load_session_plan(store, identifier)
    if plan.get("kind") == "program":
        from .programs import load_program

        return load_program(store, identifier)
    payload = {key: plan[key] for key in ("schema_version", "engine_version", "workflow", "sources")}
    fingerprint = hashlib.sha256(json_bytes(payload)).hexdigest()
    if (
        fingerprint != plan["sha256"]
        or identifier != fingerprint[:32]
        or plan["engine_version"] != __version__
    ):
        raise ValueError("Plan integrity/version mismatch; create a new plan")
    Workflow.model_validate(plan["workflow"])
    return plan
