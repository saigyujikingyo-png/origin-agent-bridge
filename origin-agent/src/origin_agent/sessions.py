"""Immutable, idempotent session commands; live Origin is owned by the worker."""

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import __version__
from .programs import load_program
from .storage import Store, file_lock, json_bytes, read_json, valid_id, write_json


class SessionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["open", "execute", "checkpoint", "restore", "close"]
    request_id: str = Field(min_length=1, max_length=160)
    session_id: str | None = None
    expected_revision: int = Field(ge=0)
    title: str = Field(default="Origin session", min_length=1, max_length=200)
    visible: bool = False
    program_plan_id: str | None = None
    checkpoint_id: str | None = None

    @model_validator(mode="after")
    def contract(self):
        if self.action == "open":
            if self.session_id or self.expected_revision != 0:
                raise ValueError("Open requires a new session and expected_revision=0")
        elif not self.session_id:
            raise ValueError("session_id is required")
        if self.session_id:
            valid_id(self.session_id)
        if self.action == "execute" and not self.program_plan_id:
            raise ValueError("Execute requires a prepared program")
        if self.program_plan_id:
            valid_id(self.program_plan_id)
            if self.action not in ("open", "execute"):
                raise ValueError("A program applies only to open/execute")
        if self.action == "restore":
            if not self.checkpoint_id:
                raise ValueError("Restore requires checkpoint_id")
            valid_id(self.checkpoint_id)
        elif self.checkpoint_id:
            raise ValueError("checkpoint_id applies only to restore")
        return self


def prepare_session(store: Store, command: SessionCommand) -> dict:
    if command.program_plan_id:
        program = load_program(store, command.program_plan_id)
        if command.action == "execute" and "__project__" in program["sources"]:
            raise ValueError(
                "A session program edits the active project; open a separate session for an input project"
            )
    request_key = hashlib.sha256(command.request_id.encode("utf-8")).hexdigest()
    session_id = command.session_id or request_key[:32]
    payload = {
        "schema_version": 3,
        "engine_version": __version__,
        "kind": "session",
        "session_id": session_id,
        "workflow": command.model_dump(),
    }
    digest = hashlib.sha256(json_bytes(payload)).hexdigest()
    identifier = digest[:32]
    with file_lock(store.root / "session-planning.lock"):
        ledger = store.root / "session-requests" / (request_key + ".json")
        if ledger.exists() and read_json(ledger)["sha256"] != digest:
            raise ValueError("request_id was already used for different content")
        plan_path = store.path("plans", identifier) / "plan.json"
        if plan_path.exists():
            load_session_plan(store, identifier)
        else:
            write_json(plan_path, {**payload, "plan_id": identifier, "sha256": digest})
        write_json(ledger, {"sha256": digest})
    return {"plan_id": identifier, "session_id": session_id, "kind": "session"}


def load_session_plan(store: Store, identifier: str) -> dict:
    plan = read_json(store.path("plans", identifier) / "plan.json")
    payload = {
        key: plan[key] for key in ("schema_version", "engine_version", "kind", "session_id", "workflow")
    }
    digest = hashlib.sha256(json_bytes(payload)).hexdigest()
    if digest != plan["sha256"] or identifier != digest[:32] or plan["engine_version"] != __version__:
        raise ValueError("Session plan integrity/version mismatch")
    if plan["kind"] != "session":
        raise ValueError("Not a session plan")
    command = SessionCommand.model_validate(plan["workflow"])
    valid_id(plan["session_id"])
    if command.program_plan_id:
        load_program(store, command.program_plan_id)
    return plan


def session_path(store: Store, identifier: str):
    return store.path("sessions", identifier) / "session.json"


def read_session(store: Store, identifier: str) -> dict:
    path = session_path(store, identifier)
    if not path.exists():
        raise ValueError("Session is not open yet; wait for its open job")
    state = read_json(path)
    public = {
        key: value
        for key, value in state.items()
        if key not in ("checkpoint_path", "recovery_path", "worker_token")
    }
    index = public.get("project_index")
    if index:
        pages = index.get("pages", [])
        graphs = index.get("graphs", [])
        public["project_index"] = {
            "page_count": len(pages),
            "graph_count": len(graphs),
            "pages": [
                {**page, "sheets": page.get("sheets", [])[:20], "sheet_count": len(page.get("sheets", []))}
                for page in pages[:40]
            ],
            "graphs": graphs[:40],
            "truncated": len(pages) > 40
            or len(graphs) > 40
            or any(len(p.get("sheets", [])) > 20 for p in pages),
        }
    return public


def interrupted_session(store: Store, plan: dict, job_id: str):
    """An interrupted worker cannot commit partial data; next use resumes its before-image."""
    path = session_path(store, plan["session_id"])
    if not path.exists():
        return
    state = read_json(path)
    if state.get("active_job") == job_id and state.get("state") == "executing":
        state.update(
            state="suspended",
            checkpoint_path=state["recovery_path"],
            checkpoint_sha256=state["recovery_sha256"],
            active_job=None,
            worker_token=None,
        )
        write_json(path, state)
