"""Single-threaded persistent Origin worker and project-scoped rollback."""

import time
import uuid
from pathlib import Path

import psutil

from . import __version__
from .native import artifact_path
from .origin_runtime import connect_origin
from .program_native import run_program, snapshot
from .programs import load_program
from .sessions import SessionCommand, load_session_plan, session_path
from .storage import Store, read_json, sha256, write_json


class SessionEngine:
    def __init__(self, store: Store, parent_alive=lambda: True):
        self.store = store
        self.runtime = None
        self.current = None
        self.parent_alive = parent_alive
        self.token = uuid.uuid4().hex

    def _save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if not self.runtime["op"].save(str(path)) or not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError("Origin could not save the session checkpoint")
        return sha256(path)

    def _working(self, identifier):
        return self.store.path("sessions", identifier) / "working.opju"

    def _resolve(self, relative, expected_hash=None):
        path = (self.store.root / relative).resolve(strict=True)
        if not path.is_relative_to(self.store.root) or not path.is_file():
            raise ValueError("Invalid session checkpoint path")
        if expected_hash and sha256(path) != expected_hash:
            raise ValueError("Session checkpoint integrity mismatch")
        return path

    def suspend(self):
        if self.runtime is None or self.current is None:
            return
        path = session_path(self.store, self.current)
        state = read_json(path)
        if state.get("worker_token") != self.token:
            self.current = None
            return
        if state.get("gui_transaction"):
            raise ValueError("Finish the active GUI transaction before switching projects")
        resume = path.parent / "recovery" / (uuid.uuid4().hex + ".opju")
        digest = self._save(resume)
        # Leave the active GUI file mutable; exported job files remain immutable.
        self._save(self._working(self.current))
        state.update(
            state="suspended",
            checkpoint_path=str(resume.relative_to(self.store.root)),
            checkpoint_sha256=digest,
            project_index=snapshot(self.runtime["op"]),
        )
        write_json(path, state)
        self.current = None

    def shutdown(self):
        if self.runtime is None:
            return
        if self.current and read_json(session_path(self.store, self.current)).get("gui_transaction"):
            # Parent loss must not enter a blocking COM save while a dialog is open.
            # The durable before-image is recovered by a later explicit rollback.
            self.runtime = None
            self.current = None
            return
        try:
            self.suspend()
        except Exception:
            # A failed save must not silently discard manual GUI edits on idle shutdown.
            self.runtime["op"].set_show(True)
            self.runtime["op"].detach()
            self.runtime = None
            raise
        self.runtime["op"].exit()
        self.runtime = None

    def _activate(self, identifier, state, command):
        if self.current == identifier:
            return
        self.suspend()
        if self.runtime is None:
            self.runtime = connect_origin(command.visible)
            write_json(self.store.root / "last-native-engine.json", self.runtime["engine"])
        op = self.runtime["op"]
        op.new()
        if command.action == "open" and command.program_plan_id:
            plan = load_program(self.store, command.program_plan_id)
            source = plan["sources"].get("__project__")
            if source:
                path = self.store.path("plans", command.program_plan_id) / source["file"]
                if not op.open(str(path)):
                    raise RuntimeError("Origin could not open the project snapshot")
        elif state.get("checkpoint_path"):
            path = self._resolve(state["checkpoint_path"], state.get("checkpoint_sha256"))
            if not op.open(str(path)):
                raise RuntimeError("Origin could not restore the session checkpoint")
        op.set_show(command.visible if command.action == "open" else state.get("visible", False))
        self._save(self._working(identifier))
        self.current = identifier

    def execute(self, job_id, plan_id):
        plan = load_session_plan(self.store, plan_id)
        command = SessionCommand.model_validate(plan["workflow"])
        identifier = plan["session_id"]
        state_path = session_path(self.store, identifier)
        directory = self.store.path("jobs", job_id)
        started = time.monotonic()
        if command.action == "open":
            if state_path.exists():
                raise ValueError("Session already exists; reuse its original open request")
            state = {
                "session_id": identifier,
                "title": command.title,
                "revision": 0,
                "visible": command.visible,
                "state": "opening",
            }
        else:
            if not state_path.exists():
                raise ValueError("Unknown session")
            state = read_json(state_path)
            if state["state"] in ("closed", "needs_attention"):
                raise ValueError("Session is closed or requires attention")
        if state["revision"] != command.expected_revision:
            raise ValueError(
                f"Stale session revision: expected {command.expected_revision}, current {state['revision']}"
            )
        original_state = dict(state)
        if not self.parent_alive():
            raise RuntimeError("Session supervisor stopped")
        if command.action == "gui":
            from .gui_session import execute_gui

            return execute_gui(self, job_id, plan, command, state)
        if state.get("gui_transaction"):
            raise ValueError("Commit or rollback the active GUI transaction before running Origin code")
        before = None
        before_hash = None
        try:
            self._activate(identifier, state, command)
            op = self.runtime["op"]
            before = state_path.parent / "recovery" / (job_id + ".opju")
            before_hash = self._save(before)
            # Origin Save without a filename must never overwrite the rollback image.
            self._save(self._working(identifier))
            pending = {
                **state,
                "state": "executing",
                "active_job": job_id,
                "recovery_path": str(before.relative_to(self.store.root)),
                "recovery_sha256": before_hash,
                "worker_token": self.token,
            }
            write_json(state_path, pending)
            write_json(
                directory / "progress.json",
                {
                    "stage": command.action,
                    "origin_pid": self.runtime["origin_pid"],
                    "origin_created": self.runtime["origin_created"],
                },
            )
            if command.action == "execute":
                run_program(self.store, job_id, command.program_plan_id, active=self.runtime)
                manifest = read_json(directory / "manifest.json")
            else:
                if command.action == "restore":
                    checkpoint, _ = artifact_path(self.store, command.checkpoint_id + "/project.opju")
                    checkpoint_manifest = read_json(checkpoint.parent / "manifest.json")
                    if checkpoint_manifest.get("session", {}).get("session_id") != identifier:
                        raise ValueError("Checkpoint belongs to another session")
                    op.new()
                    if not op.open(str(checkpoint)):
                        raise RuntimeError("Origin could not open the requested checkpoint")
                self._save(directory / "project.opju")
                manifest = {
                    "plugin_version": __version__,
                    "engine": self.runtime["engine"],
                    "workflow": command.model_dump(),
                    "project_index": snapshot(op),
                    "verification": {
                        "vendor_native": True,
                        "project_saved": True,
                        "project_reopened": False,
                        "independent_scientific_validation": False,
                    },
                    "artifacts": [
                        {
                            "name": "project.opju",
                            "bytes": (directory / "project.opju").stat().st_size,
                            "sha256": sha256(directory / "project.opju"),
                            "mime_type": "application/octet-stream",
                        }
                    ],
                }
            if not self.parent_alive():
                raise RuntimeError("Session supervisor stopped before commit")
            if (directory / "cancel.json").exists():
                raise RuntimeError("Cancelled before session commit")
            self._save(self._working(identifier))
            state = {
                **state,
                "state": "closed" if command.action == "close" else "ready",
                "revision": state["revision"] + 1,
                "last_job": job_id,
                "checkpoint_id": job_id,
                "checkpoint_path": str((directory / "project.opju").relative_to(self.store.root)),
                "checkpoint_sha256": sha256(directory / "project.opju"),
                "project_index": snapshot(op),
                "active_job": None,
                "origin_pid": self.runtime["origin_pid"],
                "updated": time.time(),
                "worker_token": self.token,
            }
            manifest.update(
                kind="session",
                job_id=job_id,
                plan_id=plan_id,
                session={key: state[key] for key in ("session_id", "revision", "state", "checkpoint_id")},
                summary=[
                    {
                        "title": state["title"],
                        "action": command.action,
                        "session_id": identifier,
                        "revision": state["revision"],
                        "results_artifact": f"{job_id}/result.json" if command.action == "execute" else None,
                    }
                ],
            )
            manifest["verification"]["seconds"] = round(time.monotonic() - started, 3)
            write_json(directory / "manifest.json", manifest)
            write_json(state_path, state)
            if command.action == "close":
                self.current = None
                self.runtime["op"].exit()
                self.runtime = None
            return {"ok": True, "session_id": identifier, "revision": state["revision"]}
        except Exception:
            if before is not None and self.runtime is not None:
                if state_path.exists() and read_json(state_path).get("worker_token") != self.token:
                    self.current = None
                    raise
                state = {**original_state, "worker_token": self.token}
                try:
                    if before_hash is None or sha256(before) != before_hash:
                        raise RuntimeError("Rollback checkpoint integrity mismatch")
                    self.runtime["op"].new()
                    if not self.runtime["op"].open(str(before)):
                        raise RuntimeError("Rollback open failed")
                    self._save(self._working(identifier))
                    state.update(
                        state="ready",
                        checkpoint_path=str(before.relative_to(self.store.root)),
                        checkpoint_sha256=sha256(before),
                        project_index=snapshot(self.runtime["op"]),
                        active_job=None,
                        last_failure=job_id,
                    )
                except Exception:
                    state.update(state="needs_attention", active_job=None, last_failure=job_id)
                write_json(state_path, state)
            raise


def serve_sessions(store: Store, runtime_dir: Path, parent_pid: int, parent_created: float):
    runtime_dir = runtime_dir.resolve(strict=True)
    if not runtime_dir.is_relative_to(store.root / "runtime"):
        raise ValueError("Invalid worker runtime directory")

    def parent_alive():
        try:
            return abs(psutil.Process(parent_pid).create_time() - parent_created) <= 0.01
        except psutil.NoSuchProcess:
            return False

    engine = SessionEngine(store, parent_alive)
    previous = None
    try:
        while not (runtime_dir / "stop.json").exists():
            if not parent_alive():
                break
            request = runtime_dir / "request.json"
            if request.exists():
                task = read_json(request)
                job_id = task["job_id"]
                receipt = store.path("jobs", job_id) / "session-completion.json"
                if job_id != previous and not receipt.exists():
                    previous = job_id
                    try:
                        result = engine.execute(job_id, task["plan_id"])
                    except Exception as exc:
                        result = {"ok": False, "error": str(exc)[:1500]}
                        error_path = receipt.parent / "error.json"
                        if not error_path.exists():
                            write_json(error_path, {"type": type(exc).__name__, "message": str(exc)[:1500]})
                    result["active_session"] = engine.current
                    result["keep_open"] = bool(
                        engine.current and read_json(session_path(store, engine.current)).get("visible")
                    )
                    write_json(receipt, result)
            time.sleep(0.05)
    finally:
        try:
            engine.shutdown()
        except Exception as exc:
            write_json(runtime_dir / "shutdown-error.json", {"message": str(exc)[:1500]})
