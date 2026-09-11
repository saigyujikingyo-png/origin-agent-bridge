"""SQLite queue + on-demand supervisor. Multiple MCP hosts share one device worker."""

import contextlib
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psutil

from .planning import load_plan
from .storage import BusyError, Store, file_lock, read_json, valid_id, write_json

TERMINAL = {"succeeded", "failed", "cancelled", "interrupted"}


@contextlib.contextmanager
def database(store: Store):
    db = sqlite3.connect(store.root / "queue.sqlite3", timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, plan_id TEXT NOT NULL UNIQUE, state TEXT NOT NULL,
            created REAL NOT NULL, updated REAL NOT NULL, error TEXT, cancel INTEGER NOT NULL DEFAULT 0
        )""")
        yield db
        db.commit()
    finally:
        db.close()


def command(*args: str) -> list[str]:
    prefix = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, "-m", "origin_agent"]
    return [*prefix, *args]


def spawn(store: Store, *args: str, stdout=None) -> subprocess.Popen:
    environment = os.environ.copy()
    environment["ORIGIN_AGENT_HOME"] = str(store.root)
    if args and args[0] in ("worker", "session-worker"):
        for name in (
            "CONTROL_PLANE_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GH_TOKEN",
            "GITHUB_TOKEN",
        ):
            environment.pop(name, None)
    if not getattr(sys, "frozen", False):
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    return subprocess.Popen(
        command(*args),
        cwd=store.root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=stdout or subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        close_fds=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def _kick_locked(store: Store):
    try:
        with file_lock(store.root / "device.lock", timeout=0):
            # Old running jobs cannot own the device lock now. Never report their partial files as success.
            with database(store) as db:
                stale = db.execute("SELECT id,plan_id FROM jobs WHERE state='running'").fetchall()
                db.execute(
                    "UPDATE jobs SET state='interrupted', error=?, updated=? WHERE state='running'",
                    (
                        "Supervisor stopped; partial results unverified. Create a revised plan to retry.",
                        time.time(),
                    ),
                )
                pending = db.execute("SELECT 1 FROM jobs WHERE state='queued' LIMIT 1").fetchone()
            for previous in stale:
                from .sessions import interrupted_session

                with contextlib.suppress(Exception):
                    plan = load_plan(store, previous["plan_id"])
                    if plan.get("kind") == "session":
                        interrupted_session(store, plan, previous["id"])
            if pending:
                spawn(store, "supervise")
    except BusyError:
        pass


def submit(store: Store, plan_id: str, *, expected_kind: str = "workflow") -> dict:
    plan = load_plan(store, plan_id)
    if plan.get("kind", "workflow") != expected_kind:
        raise ValueError("Program plans must use origin_run_program, not the fixed-workflow tool")
    with file_lock(store.root / "scheduler.lock"):
        with database(store) as db:
            existing = db.execute("SELECT id FROM jobs WHERE plan_id=?", (plan_id,)).fetchone()
            if existing:
                identifier = existing["id"]
            else:
                count = db.execute(
                    "SELECT COUNT(*) FROM jobs WHERE state IN ('queued','running')"
                ).fetchone()[0]
                if count >= 16:
                    raise BusyError("Queue is full (16 jobs); combine panels or wait for completion")
                identifier = uuid.uuid4().hex
                store.path("jobs", identifier).mkdir()
                now = time.time()
                db.execute(
                    "INSERT INTO jobs (id,plan_id,state,created,updated) VALUES (?,?,?,?,?)",
                    (identifier, plan_id, "queued", now, now),
                )
        _kick_locked(store)
    return get_job(store, identifier, kick=False)


def get_job(store: Store, identifier: str, *, kick=True) -> dict:
    valid_id(identifier)
    if kick:
        with file_lock(store.root / "scheduler.lock"):
            _kick_locked(store)
    with database(store) as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
    if row is None:
        raise ValueError("Unknown job ID")
    result = {
        "job_id": identifier,
        "plan_id": row["plan_id"],
        "state": row["state"],
        "error": row["error"],
        "cancel_requested": bool(row["cancel"]),
    }
    directory = store.path("jobs", identifier)
    progress = directory / "progress.json"
    if progress.exists():
        value = read_json(progress)
        result["progress"] = {k: v for k, v in value.items() if k not in ("origin_pid", "origin_created")}
    if row["state"] == "succeeded":
        manifest = read_json(directory / "manifest.json")
        result["summary"] = manifest["summary"]
        result["verification"] = manifest["verification"]
        if "session" in manifest:
            result["session"] = manifest["session"]
        result["artifacts"] = [
            dict(artifact_id=f"{identifier}/{a['name']}", **a) for a in manifest["artifacts"]
        ]
    else:
        result["poll_after_seconds"] = 3
        error_path = directory / "error.json"
        if row["state"] in TERMINAL and error_path.exists():
            diagnostic = read_json(error_path)
            result["diagnostic"] = {
                "type": diagnostic.get("type"),
                "labtalk_output": diagnostic.get("labtalk_output", "")[-4000:],
            }
    return result


def cancel(store: Store, identifier: str) -> dict:
    valid_id(identifier)
    with file_lock(store.root / "scheduler.lock"):
        with database(store) as db:
            row = db.execute("SELECT state FROM jobs WHERE id=?", (identifier,)).fetchone()
            if row is None:
                raise ValueError("Unknown job ID")
            if row["state"] not in TERMINAL:
                state = "cancelled" if row["state"] == "queued" else row["state"]
                db.execute(
                    "UPDATE jobs SET cancel=1,state=?,updated=? WHERE id=?", (state, time.time(), identifier)
                )
                write_json(store.path("jobs", identifier) / "cancel.json", {"requested": True})
    return get_job(store, identifier, kick=False)


def _stop_owned_origin(directory: Path):
    """Kill only the unique process identified after isolated COM activation, with PID reuse check."""
    progress_path = directory / "progress.json"
    if not progress_path.exists():
        return
    progress = read_json(progress_path)
    if not progress.get("origin_pid"):
        return
    try:
        proc = psutil.Process(progress["origin_pid"])
        if (
            abs(proc.create_time() - progress["origin_created"]) < 0.01
            and proc.name().lower() == "origin64.exe"
        ):
            proc.terminate()
            proc.wait(timeout=5)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
        pass


def supervise(store: Store):
    from .programs import load_program
    from .session_worker import SessionWorker
    from .sessions import interrupted_session

    lock_stack = contextlib.ExitStack()
    persistent = None
    idle_since = None
    idle_seconds = max(1, min(1800, int(os.environ.get("ORIGIN_AGENT_SESSION_IDLE_SECONDS", "180"))))
    try:
        lock_stack.enter_context(file_lock(store.root / "device.lock", timeout=10))
        while True:
            with file_lock(store.root / "scheduler.lock"):
                with database(store) as db:
                    row = db.execute(
                        "SELECT * FROM jobs WHERE state='queued' ORDER BY created LIMIT 1"
                    ).fetchone()
                    if row is not None:
                        identifier = row["id"]
                        db.execute(
                            "UPDATE jobs SET state='running',updated=? WHERE id=?", (time.time(), identifier)
                        )
                if row is None and persistent is None:
                    # Release under scheduler lock, so enqueue/exit cannot lose a wakeup.
                    lock_stack.close()
                    return
            if row is None:
                idle_since = idle_since or time.monotonic()
                if not persistent.active or (
                    not persistent.keep_open and time.monotonic() - idle_since >= idle_seconds
                ):
                    persistent.stop()
                    persistent = None
                else:
                    time.sleep(0.1)
                continue
            idle_since = None
            directory = store.path("jobs", identifier)
            plan = None
            session_command = False
            receipt = None
            try:
                plan = load_plan(store, row["plan_id"])
                session_command = plan.get("kind") == "session"
                timeout = 180
                if session_command and plan["workflow"].get("program_plan_id"):
                    timeout = load_program(store, plan["workflow"]["program_plan_id"])["workflow"][
                        "timeout_seconds"
                    ]
                elif not session_command:
                    timeout = plan["workflow"]["timeout_seconds"]
                started = time.monotonic()
                reason = None
                with (directory / "worker.log").open("wb") as log:
                    if session_command:
                        if persistent is None or persistent.process.poll() is not None:
                            if persistent is not None:
                                persistent.discard()
                            persistent = SessionWorker(store)
                        persistent.submit(identifier, row["plan_id"])
                        worker = persistent.process
                    else:
                        if persistent is not None:
                            persistent.stop()
                            persistent = None
                        worker = spawn(store, "worker", identifier, row["plan_id"], stdout=log)
                    while worker.poll() is None:
                        if session_command:
                            receipt = persistent.completed(directory)
                            if receipt is not None:
                                break
                        if (directory / "cancel.json").exists():
                            reason = "cancelled"
                        elif time.monotonic() - started > timeout:
                            reason = "timeout"
                        if reason:
                            # A cooperative exit gets a short grace period, including the COM finally block.
                            write_json(directory / "cancel.json", {"requested": True})
                            grace = time.monotonic() + 2
                            while worker.poll() is None and time.monotonic() < grace:
                                if session_command and persistent.completed(directory) is not None:
                                    receipt = persistent.completed(directory)
                                    break
                                time.sleep(0.05)
                            if worker.poll() is None and receipt is None:
                                worker.terminate()
                                worker.wait(timeout=5)
                                _stop_owned_origin(directory)
                            if session_command and receipt is None:
                                interrupted_session(store, plan, identifier)
                                persistent.discard()
                                persistent = None
                            break
                        time.sleep(0.2)
                if reason:
                    state, error = ("cancelled" if reason == "cancelled" else "failed"), reason
                elif (receipt and receipt["ok"] or not session_command and worker.returncode == 0) and (
                    directory / "manifest.json"
                ).exists():
                    state, error = "succeeded", None
                else:
                    state = "failed"
                    error_path = directory / "error.json"
                    error = (
                        read_json(error_path)["message"]
                        if error_path.exists()
                        else "Native worker stopped unexpectedly"
                    )
                    if session_command and receipt is None:
                        interrupted_session(store, plan, identifier)
            except Exception as exc:
                state, error = "failed", str(exc)[:1500]
            with database(store) as db:
                # A cancel requested between worker exit and final state commit still wins.
                requested = db.execute("SELECT cancel FROM jobs WHERE id=?", (identifier,)).fetchone()[0]
                if requested and not (session_command and receipt and receipt["ok"]):
                    state, error = "cancelled", "cancelled"
                elif requested and session_command and receipt and receipt["ok"]:
                    state, error = "succeeded", "Cancellation arrived after the verified session commit"
                db.execute(
                    "UPDATE jobs SET state=?,error=?,updated=? WHERE id=?",
                    (state, error, time.time(), identifier),
                )
    except BusyError:
        return
    finally:
        if persistent is not None:
            with contextlib.suppress(Exception):
                persistent.stop()
        lock_stack.close()
