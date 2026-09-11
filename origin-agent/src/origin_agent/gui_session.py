"""GUI transactions keep COM idle while dialogs are open."""

import time

import psutil

from . import __version__
from .gui import INPUT_ACTIONS, VISUAL_ACTIONS, public_observation, resolve_target
from .gui_native import NativeGui
from .origin_runtime import release_terminated_origin
from .program_native import snapshot
from .sessions import session_path
from .storage import read_json, sha256, write_json


def execute_gui(engine, job_id, plan, command, state):
    store, identifier = engine.store, plan["session_id"]
    path = session_path(store, identifier)
    directory = store.path("jobs", job_id)
    request = command.gui
    action = request.action
    transaction = state.get("gui_transaction")
    if action == "begin" and transaction:
        raise ValueError("A GUI transaction is already open; observe or finish it")
    if action != "begin" and not transaction:
        raise ValueError("Begin a GUI transaction before observing or changing the interface")
    if transaction and (engine.current != identifier or engine.runtime is None) and action != "rollback":
        raise ValueError("GUI worker is no longer live; rollback to its saved checkpoint")
    if action == "begin":
        engine._activate(identifier, state, command)
        engine.runtime["op"].set_show(True)
    elif action == "rollback" and (engine.current != identifier or engine.runtime is None):
        if transaction.get("origin_pid") and psutil.pid_exists(transaction["origin_pid"]):
            # The old worker can vanish while its visible COM server survives. Explicit rollback owns it.
            NativeGui(transaction).terminate_owned()
        engine._activate(identifier, state, command)
    backend = NativeGui(engine.runtime)
    current = backend.observe(request.query)
    target = None
    if action in INPUT_ACTIONS:
        if state.get("gui_observation_id") != request.observation_id:
            raise ValueError("GUI observation is no longer current; observe again")
        previous = read_json(store.path("jobs", request.observation_id) / "gui-private.json")
        # Re-run the original filter: never accept a guessed handle or a newly discovered target.
        current = backend.observe(previous["query"])
        target = resolve_target(previous, current, request.target_id)
        if action in VISUAL_ACTIONS:
            from .gui_input import capture_target

            capture = capture_target(previous, current, target)
    if action in ("begin", "commit") and current["blocked"]:
        raise ValueError("Close the Origin dialog before beginning or committing a GUI transaction")
    started = time.monotonic()
    if action == "begin":
        before = directory / "project.opju"
        digest = engine._save(before)
        engine._save(engine._working(identifier))
        transaction = {
            "path": str(before.relative_to(store.root)),
            "sha256": digest,
            "origin_pid": engine.runtime["origin_pid"],
            "origin_created": engine.runtime["origin_created"],
        }
        state = {
            **state,
            "gui_transaction": transaction,
            "worker_token": engine.token,
            "recovery_path": transaction["path"],
            "recovery_sha256": digest,
            "checkpoint_path": transaction["path"],
            "checkpoint_sha256": digest,
            "checkpoint_id": job_id,
            "visible": True,
        }
    pending = {
        **state,
        "state": "executing",
        "active_job": job_id,
        "worker_token": engine.token,
        "gui_observation_id": None,
        "recovery_path": transaction["path"],
        "recovery_sha256": transaction["sha256"],
    }
    write_json(path, pending)
    write_json(
        directory / "progress.json",
        {
            "stage": "gui_" + action,
            "origin_pid": engine.runtime["origin_pid"],
            "origin_created": engine.runtime["origin_created"],
        },
    )
    try:
        if action == "invoke":
            backend.invoke(target)
        elif action == "set_text":
            backend.set_text(target, request.text)
        elif action == "dismiss":
            backend.dismiss(target)
        elif action in ("select", "toggle", "expand", "collapse"):
            backend.accessibility.action(target, action)
        elif action in VISUAL_ACTIONS:
            from .gui_input import VisualInput

            VisualInput(backend, target, capture).execute(request)
        elif action == "rollback":
            before = engine._resolve(transaction["path"], transaction["sha256"])
            if current["blocked"]:
                # Explicit rollback may discard the unfinished dialog, never another Origin process.
                backend.terminate_owned()
                release_terminated_origin(engine.runtime)
                engine.runtime = None
                engine.current = None
                engine._activate(
                    identifier,
                    {
                        **state,
                        "checkpoint_path": transaction["path"],
                        "checkpoint_sha256": transaction["sha256"],
                    },
                    command,
                )
                backend = NativeGui(engine.runtime)
                write_json(
                    directory / "progress.json",
                    {
                        "stage": "gui_rollback",
                        "origin_pid": engine.runtime["origin_pid"],
                        "origin_created": engine.runtime["origin_created"],
                    },
                )
            else:
                engine.runtime["op"].new()
                if not engine.runtime["op"].open(str(before)):
                    raise RuntimeError("Origin could not restore the GUI checkpoint")
        if action in INPUT_ACTIONS:
            # Bound settling time; successful dispatch is not semantic success.
            deadline = time.monotonic() + 3
            initial = (current["windows"], current["targets"])
            stable_since = None
            while True:
                time.sleep(0.1)
                current = backend.observe(previous["query"])
                latest = (current["windows"], current["targets"])
                if latest == initial:
                    stable_since = stable_since or time.monotonic()
                else:
                    stable_since = None
                if (stable_since and time.monotonic() - stable_since >= 0.15) or time.monotonic() >= deadline:
                    break
                initial = latest
            current = backend.observe(request.query)
        else:
            current = backend.observe(request.query)
        if not engine.parent_alive() or (directory / "cancel.json").exists():
            raise RuntimeError("GUI command interrupted; observe before continuing")
        completed = action in ("commit", "rollback")
        if completed:
            engine._save(directory / "project.opju")
            engine._save(engine._working(identifier))
            state.update(
                checkpoint_path=str((directory / "project.opju").relative_to(store.root)),
                checkpoint_sha256=sha256(directory / "project.opju"),
                checkpoint_id=job_id,
                project_index=snapshot(engine.runtime["op"]),
                gui_transaction=None,
            )
            current = backend.observe(request.query)
        view = public_observation(current)
        view["observation_id"] = job_id
        if request.screenshot:
            try:
                current["capture"] = backend.capture(current, directory / "gui.png")
                view["capture"] = current["capture"]
                view["screenshot_window_id"] = current["capture"]["window_id"]
                view["screenshot_artifact_id"] = f"{job_id}/gui.png"
            except OSError as exc:
                # Preview availability is separate from a committed project or delivered input.
                (directory / "gui.png").unlink(missing_ok=True)
                view["screenshot_error"] = str(exc)
        write_json(directory / "gui-private.json", current)
        write_json(directory / "gui.json", view)
        state.update(
            state="ready" if completed else "gui",
            revision=state["revision"] + 1,
            gui_observation_id=None if completed else job_id,
            active_job=None,
            worker_token=engine.token,
            last_job=job_id,
            origin_pid=engine.runtime["origin_pid"],
            updated=time.time(),
        )
        session = {k: state[k] for k in ("session_id", "revision", "state", "checkpoint_id")}
        artifacts = []
        for name, mime in (
            ("gui.json", "application/json"),
            ("gui.png", "image/png"),
            ("project.opju", "application/octet-stream"),
        ):
            output = directory / name
            if output.exists():
                artifacts.append(
                    {
                        "name": name,
                        "bytes": output.stat().st_size,
                        "sha256": sha256(output),
                        "mime_type": mime,
                    }
                )
        manifest = {
            "plugin_version": __version__,
            "kind": "session",
            "job_id": job_id,
            "plan_id": plan["plan_id"],
            "engine": engine.runtime["engine"],
            "session": session,
            "gui": view,
            "artifacts": artifacts,
            "summary": [{"action": "gui_" + action, "session_id": identifier, "revision": state["revision"]}],
            "verification": {
                "vendor_native": True,
                "gui_observed": True,
                "screenshot_captured": "screenshot_artifact_id" in view,
                "project_saved": action == "begin" or completed,
                "project_reopened": action == "rollback",
                "gui_semantic_success": "requires task-specific readback",
                "independent_scientific_validation": False,
                "seconds": round(time.monotonic() - started, 3),
            },
        }
        write_json(directory / "manifest.json", manifest)
        write_json(path, state)
        return {"ok": True, "session_id": identifier, "revision": state["revision"]}
    except Exception:
        # A dialog may be open: do not invoke COM rollback from a GUI error handler.
        if read_json(path).get("worker_token") == engine.token:
            write_json(
                path,
                {
                    **pending,
                    "state": "gui",
                    "active_job": None,
                    "revision": state["revision"] + 1,
                    "last_failure": job_id,
                },
            )
        raise
