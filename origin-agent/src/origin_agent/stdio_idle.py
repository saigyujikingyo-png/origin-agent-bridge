"""Adapter-side, fail-closed admission for cooperative stdio retirement.

This is private to one owned adapter. It neither stops native processes
nor updates queue/session state. The existing scheduler and device locks fence
new scientific work while an idle worker acknowledges and exits.
"""

import contextlib
import hmac
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from .storage import file_lock


class IdleControl:
    def __init__(self, root, token, *, lease_seconds=5.0, clock=time.monotonic):
        if not isinstance(token, str) or len(token) < 32:
            raise ValueError("A private worker token is required")
        self.root = Path(root).resolve()
        self.token = token
        self.clock = clock
        self.lease_seconds = lease_seconds
        self.condition = threading.Condition(threading.RLock())
        self.active = 0
        self.uncertain = False
        self.closed = False
        self.lease = None
        self.deadline = None
        self.stack = None
        self.committed = False
        self.watcher = threading.Thread(target=self._watch, daemon=True)
        self.watcher.start()

    @contextlib.contextmanager
    def application_call(self):
        with self.condition:
            self._expire()
            if self.closed or self.lease is not None:
                raise RuntimeError("Worker has entered an idle admission transaction")
            self.active += 1
        try:
            yield
        except BaseException:
            # In particular, cancellation of to_thread does not prove its work stopped.
            self.mark_uncertain()
            raise
        finally:
            with self.condition:
                self.active -= 1

    def mark_uncertain(self):
        with self.condition:
            self.uncertain = True

    def _release(self):
        stack, self.stack = self.stack, None
        self.lease = self.deadline = None
        self.committed = False
        if stack is not None:
            try:
                stack.close()
            except Exception:
                self.uncertain = True
        self.condition.notify_all()

    def _expire(self):
        if self.deadline is not None and self.clock() >= self.deadline:
            self._release()

    def _watch(self):
        with self.condition:
            while not self.closed:
                self._expire()
                delay = None if self.deadline is None else max(0.001, self.deadline - self.clock())
                self.condition.wait(delay)

    def _within_root(self, path):
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise ValueError("Unconfirmed state ownership")

    def _state_reason(self):
        """Read only bounded execution metadata, never artifacts or native applications."""
        database = self.root / "queue.sqlite3"
        self._within_root(database)
        if database.exists():
            with contextlib.closing(
                sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=0)
            ) as db:
                states = {row[0] for row in db.execute("SELECT DISTINCT state FROM jobs")}
            if states & {"queued", "running"}:
                return "scientific_work_pending"
            if states - {"succeeded", "failed", "cancelled", "interrupted"}:
                return "execution_state_unknown"
        elif any((self.root / "jobs").iterdir()):
            return "execution_state_unknown"
        sessions = self.root / "sessions"
        self._within_root(sessions)
        for number, directory in enumerate(sessions.iterdir()):
            if number >= 4096:
                return "execution_state_unknown"
            self._within_root(directory)
            path = directory / "session.json"
            self._within_root(path)
            if not directory.is_dir() or not path.is_file() or path.stat().st_size > 1024 * 1024:
                return "session_state_unknown"
            state = json.loads(path.read_text(encoding="utf-8"))
            if state.get("active_job") or state.get("gui_transaction"):
                return "session_work_pending"
            if state.get("state") not in {"closed", "suspended"}:
                return "session_retained"
        return None

    def handle(self, arguments):
        if (
            not isinstance(arguments, dict)
            or not isinstance(arguments.get("token"), str)
            or not hmac.compare_digest(arguments["token"], self.token)
        ):
            return {"allowed": False, "reason": "private_control_required"}
        with self.condition:
            self._expire()
            if self.closed:
                return {"allowed": False, "reason": "worker_closed"}
            action = arguments.get("action")
            if action == "prepare":
                if self.active or self.uncertain or self.lease is not None:
                    return {"allowed": False, "reason": "worker_retained"}
                stack = contextlib.ExitStack()
                try:
                    stack.enter_context(file_lock(self.root / "scheduler.lock", timeout=0))
                    stack.enter_context(file_lock(self.root / "device.lock", timeout=0))
                    reason = self._state_reason()
                    if reason:
                        stack.close()
                        return {"allowed": False, "reason": reason}
                except Exception:
                    stack.close()
                    return {"allowed": False, "reason": "execution_state_unconfirmed"}
                self.stack = stack
                self.lease = uuid.uuid4().hex
                self.deadline = self.clock() + self.lease_seconds
                self.condition.notify_all()
                return {"allowed": True, "lease": self.lease, "deadline": self.deadline}
            if action not in {"commit", "abort"} or arguments.get("lease") != self.lease or not self.lease:
                return {"allowed": False, "reason": "lease_unconfirmed"}
            if action == "abort":
                self._release()
                return {"allowed": True, "state": "aborted"}
            if self.active or self.uncertain:
                self._release()
                return {"allowed": False, "reason": "worker_retained"}
            self.committed = True
            return {"allowed": True, "state": "committed", "deadline": self.deadline}

    def close(self):
        with self.condition:
            self.closed = True
            self._release()
        self.watcher.join(timeout=1)

    def retire(self, close_stdin):
        """Atomically retain the state fences across expiry-check and cooperative EOF.

        The caller has already drained both RPC directions and received a quiet
        ping barrier from a fingerprint-bound Origin backend. No other thread can
        expire the lease between this check and closing this owned input pipe.
        """
        with self.condition:
            self._expire()
            if not self.committed or self.lease is None or self.uncertain or self.active:
                return False
            close_stdin()
            return True
