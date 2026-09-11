"""Supervisor-side lifecycle for the persistent, single-threaded native worker."""

import os
import uuid

import psutil

from .storage import read_json, write_json


class SessionWorker:
    def __init__(self, store):
        from .jobs import spawn

        self.directory = store.root / "runtime" / uuid.uuid4().hex
        self.directory.mkdir(parents=True)
        self.log = (self.directory / "worker.log").open("wb")
        self.process = spawn(
            store,
            "session-worker",
            str(self.directory),
            str(os.getpid()),
            str(psutil.Process().create_time()),
            stdout=self.log,
        )
        self.active = False
        self.session_id = None
        self.keep_open = False

    def submit(self, job_id, plan_id):
        write_json(self.directory / "request.json", {"job_id": job_id, "plan_id": plan_id})

    def completed(self, directory):
        path = directory / "session-completion.json"
        if not path.exists():
            return None
        result = read_json(path)
        self.active = bool(result.get("active_session"))
        self.session_id = result.get("active_session")
        self.keep_open = bool(result.get("keep_open"))
        return result

    def stop(self):
        if self.process.poll() is None:
            write_json(self.directory / "stop.json", {"requested": True})
            self.process.wait(timeout=15)
        self.log.close()

    def discard(self):
        self.active = False
        self.session_id = None
        self.log.close()
