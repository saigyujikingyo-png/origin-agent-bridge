import base64
import hashlib
import json

import pytest
from mcp import Client

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


def completed_artifact(store, payload):
    job = "c" * 32
    folder = store.path("jobs", job)
    folder.mkdir()
    path = folder / "project.opju"
    path.write_bytes(payload)
    with database(store) as db:
        db.execute(
            "INSERT INTO jobs (id,plan_id,state,created,updated) VALUES (?,?,?,?,?)",
            (job, "d" * 32, "succeeded", 0.0, 0.0),
        )
    write_json(
        folder / "manifest.json",
        {
            "summary": [],
            "verification": {},
            "artifacts": [
                {"name": path.name, "mime_type": "application/octet-stream", "sha256": sha256(path)}
            ],
        },
    )
    return job, path


@pytest.mark.anyio
@pytest.mark.parametrize("profile", ["full", "economy"])
async def test_download_transfers_exact_binary_without_text_expansion(store, profile):
    from origin_agent.server import make_server

    payload = bytes(range(256)) * 512
    job, path = completed_artifact(store, payload)
    async with Client(make_server(store, profile=profile, vision="off")) as client:
        result = await client.call_tool(
            "origin_get_artifact", {"artifact_id": f"{job}/project.opju", "mode": "download"}
        )
        assert not result.is_error
        embedded = [c.resource for c in result.content if c.type == "resource"]
        assert len(embedded) == 1
        assert base64.b64decode(embedded[0].blob, validate=True) == payload
        info = json.loads(next(c.text for c in result.content if c.type == "text"))
        assert info["bytes"] == len(payload)
        assert info["sha256"] == hashlib.sha256(payload).hexdigest()
        assert sum(len(c.text) for c in result.content if c.type == "text") < 1024
        info_only = await client.call_tool("origin_get_artifact", {"artifact_id": f"{job}/project.opju"})
        assert not any(c.type == "resource" for c in info_only.content)
        for artifact_id in (f"{job}/../project.opju", f"{job}/state.json"):
            assert (
                await client.call_tool(
                    "origin_get_artifact", {"artifact_id": artifact_id, "mode": "download"}
                )
            ).is_error
        path.write_bytes(b"tampered")
        assert (
            await client.call_tool(
                "origin_get_artifact", {"artifact_id": f"{job}/project.opju", "mode": "download"}
            )
        ).is_error


@pytest.mark.anyio
async def test_download_rejects_unfinished_job_and_oversize(store):
    from origin_agent.server import make_server

    job, path = completed_artifact(store, b"x")
    with database(store) as db:
        db.execute("UPDATE jobs SET state='failed' WHERE id=?", (job,))
    async with Client(make_server(store)) as client:
        request = {"artifact_id": f"{job}/project.opju", "mode": "download"}
        assert (await client.call_tool("origin_get_artifact", request)).is_error
        with database(store) as db:
            db.execute("UPDATE jobs SET state='succeeded' WHERE id=?", (job,))
        with path.open("wb") as stream:
            stream.truncate(32 * 1024 * 1024 + 1)
        manifest = json.loads((path.parent / "manifest.json").read_text())
        manifest["artifacts"][0]["sha256"] = sha256(path)
        write_json(path.parent / "manifest.json", manifest)
        result = await client.call_tool("origin_get_artifact", request)
        assert result.is_error and "32 MiB" in str(result)


def test_binary_rejects_changes_after_initial_path_check(store, monkeypatch):
    from origin_agent import native

    job, path = completed_artifact(store, b"original")
    original = native.artifact_path

    def changing_path(*args):
        result = original(*args)
        path.write_bytes(b"changed after initial verification")
        return result

    monkeypatch.setattr(native, "artifact_path", changing_path)
    with pytest.raises(ValueError, match="changed during transfer"):
        native.artifact_bytes(store, f"{job}/project.opju")


def test_artifact_symlinks_rejected(store, tmp_path):
    job, path = completed_artifact(store, b"same bytes")
    outside = tmp_path / "outside.opju"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("Creating symlinks requires Windows developer mode or privilege")
    with pytest.raises(ValueError, match="links are not permitted"):
        artifact_path(store, f"{job}/project.opju")
