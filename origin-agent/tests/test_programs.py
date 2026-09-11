import pytest
from pydantic import ValidationError

from origin_agent import jobs
from origin_agent.capabilities import api_index
from origin_agent.planning import load_plan
from origin_agent.programs import OriginProgram, Readback, check_readback, load_program, prepare_program
from origin_agent.storage import read_json, write_json


def spec(**changes):
    return OriginProgram(title="test", language="python", code="RESULTS['n'] = 4", **changes)


def test_program_input_snapshot_and_idempotency(store, tmp_path, monkeypatch):
    source = tmp_path / "data.txt"
    source.write_text("original")
    program = spec(inputs={"data": str(source)})
    first = prepare_program(store, program)
    assert prepare_program(store, program) == first
    source.write_text("changed")
    plan = load_plan(store, first["plan_id"])
    assert plan["kind"] == "program"
    assert (store.path("plans", first["plan_id"]) / plan["sources"]["data"]["file"]).read_text() == "original"
    monkeypatch.setattr(jobs, "spawn", lambda *a, **k: None)
    with pytest.raises(ValueError, match="origin_run_program"):
        jobs.submit(store, first["plan_id"])
    one = jobs.submit(store, first["plan_id"], expected_kind="program")
    two = jobs.submit(store, first["plan_id"], expected_kind="program")
    assert one["job_id"] == two["job_id"]
    assert jobs.cancel(store, one["job_id"])["state"] == "cancelled"


def test_program_tampering_is_rejected(store, tmp_path):
    source = tmp_path / "data.dat"
    source.write_text("original")
    prepared = prepare_program(store, spec(inputs={"data": str(source)}))
    directory = store.path("plans", prepared["plan_id"])
    plan = read_json(directory / "plan.json")
    (directory / plan["sources"]["data"]["file"]).write_text("tampered")
    with pytest.raises(ValueError, match="snapshot integrity"):
        load_program(store, prepared["plan_id"])
    plan["workflow"]["code"] = "RESULTS['n']=5"
    write_json(directory / "plan.json", plan)
    with pytest.raises(ValueError, match="integrity"):
        load_program(store, prepared["plan_id"])


@pytest.mark.parametrize("name", ["../out.txt", "C:\\out.txt", "manifest.json", "project.opju", "x:stream"])
def test_program_cannot_publish_reserved_or_external_output(name):
    with pytest.raises(ValidationError):
        spec(output_files=[name])


def test_program_checks_and_contracts():
    with pytest.raises(ValidationError):
        OriginProgram(title="C", language="origin_c", code="void test() {}")
    with pytest.raises((SyntaxError, ValidationError)):
        OriginProgram(title="Python", language="python", code="def x(")
    with pytest.raises(ValidationError):
        spec(project_path="a.opju", project_artifact="x/project.opju")
    assert check_readback(4, Readback(expression="2*2", expected=4)) == 4
    with pytest.raises(RuntimeError, match="postcondition"):
        check_readback(5, Readback(expression="2*2", expected=4))
    with pytest.raises(RuntimeError, match="finite"):
        check_readback(float("nan"), Readback(expression="unknown"))


def test_capability_ast_does_not_import_or_execute_vendor_code(tmp_path):
    (tmp_path / "api.py").write_text(
        'raise RuntimeError("must not import")\n'
        'def plot(x, color="red"):\n    """Plot sample data."""\n    pass\n'
    )
    rows = api_index(tmp_path)
    assert rows[0]["name"] == "plot"
    assert rows[0]["help"] == "Plot sample data."


def test_worker_environment_omits_provider_credentials(store, monkeypatch):
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "test-only-not-a-real-key")
    captured = {}
    monkeypatch.setattr(jobs.subprocess, "Popen", lambda *a, **k: captured.update(k))
    jobs.spawn(store, "worker", "a" * 32, "b" * 32)
    assert "CONTROL_PLANE_API_KEY" not in captured["env"]
