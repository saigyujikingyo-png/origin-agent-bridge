import pytest

from origin_agent.jobs import database
from origin_agent.native import artifact_path
from origin_agent.storage import sha256, write_json


def test_artifact_traversal_and_tamper_are_rejected(store):
    job = "a" * 32
    folder = store.path("jobs", job)
    folder.mkdir()
    artifact = folder / "result.csv"
    artifact.write_text("x,y\n1,2\n", encoding="utf-8")
    with database(store) as db:
        db.execute(
            "INSERT INTO jobs (id,plan_id,state,created,updated) VALUES (?,?,?,?,?)",
            (job, "b" * 32, "succeeded", 0.0, 0.0),
        )
    write_json(
        folder / "manifest.json",
        {
            "summary": [],
            "verification": {},
            "artifacts": [{"name": "result.csv", "mime_type": "text/csv", "sha256": sha256(artifact)}],
        },
    )
    assert artifact_path(store, f"{job}/result.csv")[0] == artifact
    with pytest.raises(ValueError, match="Invalid artifact"):
        artifact_path(store, f"{job}/../result.csv")
    artifact.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        artifact_path(store, f"{job}/result.csv")
