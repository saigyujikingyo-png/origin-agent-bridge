"""General Origin programs: immutable inputs and honest, explicit verification contracts.

Programs run with the Windows user's permissions, not in a security sandbox.
The managed queue and output checks prevent accidental result confusion; they do
not constrain arbitrary Python, LabTalk, Origin C or native extension code.
"""

import hashlib
import math
import shutil
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import __version__
from .storage import Store, json_bytes, read_json, sha256, write_json


class Readback(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    expression: str = Field(min_length=1, max_length=1024)
    type: Literal["number", "string"] = "number"
    expected: float | str | None = None
    tolerance: float = Field(default=1e-8, ge=0, le=1e6)


class OriginProgram(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    title: str = Field(min_length=1, max_length=200)
    language: Literal["python", "labtalk", "origin_c"]
    code: str = Field(min_length=1, max_length=131072)
    entrypoint: str | None = Field(default=None, max_length=8192)
    inputs: dict[str, str] = Field(default_factory=dict, max_length=32)
    project_path: str | None = None
    project_artifact: str | None = None
    readbacks: dict[str, Readback] = Field(default_factory=dict, max_length=32)
    graph_formats: list[Literal["png", "pdf", "svg"]] = Field(default_factory=lambda: ["png"], max_length=3)
    output_files: list[str] = Field(default_factory=list, max_length=32)
    timeout_seconds: int = Field(default=180, ge=10, le=3600)
    revision: str = Field(default="1", min_length=1, max_length=80)

    @field_validator("inputs")
    @classmethod
    def aliases(cls, value):
        if any(not name.isidentifier() or len(name) > 64 or name == "__project__" for name in value):
            raise ValueError("Input aliases must be identifiers of at most 64 characters")
        return value

    @field_validator("output_files")
    @classmethod
    def filenames(cls, value):
        reserved = {
            "project.opju",
            "manifest.json",
            "result.json",
            "state.json",
            "progress.json",
            "error.json",
            "cancel.json",
            "worker.log",
            "program.py",
            "program.ogs",
            "program.c",
            "labtalk.log",
            "source-project.opju",
            "source-project.opj",
        }
        for name in value:
            if (
                not name
                or len(name) > 180
                or Path(name).name != name
                or any(c in name for c in '/\\:< >|?*"'.replace(" ", ""))
                or name.endswith((".", " "))
                or name.lower() in reserved
                or name.lower().startswith("graph-")
            ):
                raise ValueError("Output files must be non-reserved filenames in the job directory")
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def contract(self):
        if self.project_path and self.project_artifact:
            raise ValueError("Choose project_path or project_artifact, not both")
        if self.language == "origin_c" and not self.entrypoint:
            raise ValueError("Origin C requires LabTalk entrypoint code to call the compiled functions")
        if self.language != "origin_c" and self.entrypoint:
            raise ValueError("entrypoint applies only to Origin C")
        if self.language == "python":
            compile(self.code, "<origin-program>", "exec")
        return self


def prepare_program(store: Store, program: OriginProgram) -> dict:
    from .native import artifact_path

    files = {alias: store.input_path(path, data_only=False) for alias, path in program.inputs.items()}
    project = None
    if program.project_path:
        project = store.input_path(program.project_path, data_only=False)
    elif program.project_artifact:
        project, _ = artifact_path(store, program.project_artifact)
    if project:
        if project.suffix.lower() not in (".opj", ".opju"):
            raise ValueError("Project inputs must be OPJ/OPJU")
        files["__project__"] = project
    sources = {}
    for index, (alias, path) in enumerate(files.items()):
        if path.stat().st_size > 256 * 1024 * 1024:
            raise ValueError("Each program input must be <=256 MiB")
        sources[alias] = {
            "name": path.name,
            "file": f"input-{index}{path.suffix.lower()}",
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
    payload = {
        "schema_version": 2,
        "engine_version": __version__,
        "kind": "program",
        "workflow": program.model_dump(),
        "sources": sources,
    }
    fingerprint = hashlib.sha256(json_bytes(payload)).hexdigest()
    identifier = fingerprint[:32]
    directory = store.path("plans", identifier)
    # Serialize first-time snapshot creation. Never overwrite a submitted plan's files.
    from .storage import file_lock

    with file_lock(store.root / "program-planning.lock"):
        if not (directory / "plan.json").exists():
            directory.mkdir(exist_ok=True)
            for alias, path in files.items():
                target = directory / sources[alias]["file"]
                shutil.copyfile(path, target)
                if sha256(target) != sources[alias]["sha256"]:
                    raise ValueError("Input changed while taking a snapshot; retry preparation")
            write_json(directory / "plan.json", {**payload, "plan_id": identifier, "sha256": fingerprint})
    return {"plan_id": identifier, "sha256": fingerprint, "kind": "program"}


def load_program(store: Store, identifier: str) -> dict:
    directory = store.path("plans", identifier)
    plan = read_json(directory / "plan.json")
    payload = {key: plan[key] for key in ("schema_version", "engine_version", "kind", "workflow", "sources")}
    fingerprint = hashlib.sha256(json_bytes(payload)).hexdigest()
    if (
        fingerprint != plan["sha256"]
        or identifier != fingerprint[:32]
        or plan["engine_version"] != __version__
        or plan["kind"] != "program"
    ):
        raise ValueError("Program integrity/version mismatch; prepare again")
    OriginProgram.model_validate(plan["workflow"])
    for source in plan["sources"].values():
        path = directory / source["file"]
        if path.parent != directory or sha256(path) != source["sha256"]:
            raise ValueError("Program snapshot integrity mismatch")
    return plan


def check_readback(value, check: Readback):
    if check.type == "number":
        value = float(value)
        if not math.isfinite(value):
            raise RuntimeError("Origin readback is not a finite number")
    if check.expected is not None:
        matches = (
            math.isclose(value, float(check.expected), rel_tol=check.tolerance, abs_tol=check.tolerance)
            if check.type == "number"
            else str(value) == str(check.expected)
        )
        if not matches:
            raise RuntimeError(
                f"Origin postcondition failed: {check.expression}; expected {str(check.expected)[:100]}, "
                f"got {str(value)[:100]}"
            )
    return value
