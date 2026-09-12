"""Small, reversible host integration. No credentials, telemetry or model calls."""

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from . import __version__
from .storage import read_json, valid_id, write_json


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def contents(path):
    return path.read_bytes() if path.exists() else None


def atomic_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_bytes(data)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def host_config(path, entry):
    raw = contents(path)
    config = json.loads(raw.decode("utf-8-sig")) if raw is not None else {}
    if not isinstance(config, dict) or not isinstance(config.get("mcpServers", {}), dict):
        raise ValueError(f"Invalid host configuration structure: {path}")
    config.setdefault("mcpServers", {})["origin-agent"] = entry
    return encoded(config)


class Changes:
    def __init__(self, state_root):
        self.root = Path(state_root) / "installations" / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.path = self.root / "receipt.json"
        self.value = {"id": self.root.name, "status": "preparing", "files": []}
        self.save()

    def save(self):
        write_json(self.path, self.value)

    def prepare(self, path, data):
        path = path.resolve()
        before = contents(path)
        backup = f"{len(self.value['files'])}.bin" if before is not None else None
        if backup:
            atomic_bytes(self.root / backup, before)
        item = {"path": str(path), "before": digest(before), "after": digest(data), "backup": backup}
        self.value["files"].append(item)
        self.save()
        return item

    def put(self, path, data):
        item = self.prepare(path, data)
        if digest(contents(path)) != item["before"]:
            raise RuntimeError(f"Configuration changed during installation: {path}")
        atomic_bytes(path, data)

    def codex(self, executable, state_root, user_home):
        command = shutil.which("codex")
        if not command:
            raise RuntimeError("Codex CLI was not found. Install it or select another host.")
        config = user_home / ".codex/config.toml"
        item = self.prepare(config, contents(config))
        try:
            result = subprocess.run(
                [
                    command,
                    "mcp",
                    "add",
                    "origin-agent",
                    "--env",
                    f"ORIGIN_AGENT_HOME={state_root}",
                    "--",
                    str(executable),
                    "serve",
                ],
                capture_output=True,
                timeout=60,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        finally:
            item["after"] = digest(contents(config))
            self.save()
        if result.returncode:
            raise RuntimeError("Codex CLI could not register Origin Companion; configuration was backed up")


def rollback(state_root, receipt_id):
    valid_id(receipt_id)
    root = Path(state_root) / "installations" / receipt_id
    path = root / "receipt.json"
    receipt = read_json(path)
    if receipt["status"] == "rolled_back":
        return {"receipt_id": receipt_id, "status": "rolled_back"}
    # Check every file before changing any; never overwrite edits made after installation.
    restore = []
    for item in receipt["files"]:
        target = Path(item["path"])
        current = digest(contents(target))
        if current == item["before"]:
            continue
        if current != item["after"]:
            raise RuntimeError(f"Rollback conflict; file changed since installation: {target}")
        backup = item["backup"]
        data = contents(root / Path(backup).name) if backup else None
        if digest(data) != item["before"]:
            raise RuntimeError("Installation backup failed integrity verification")
        restore.append((target, data))
    for target, data in reversed(restore):
        if data is None:
            target.unlink(missing_ok=True)
        else:
            atomic_bytes(target, data)
    receipt["status"] = "rolled_back"
    write_json(path, receipt)
    return {"receipt_id": receipt_id, "status": "rolled_back", "restored_files": len(restore)}


def integrate(bundle, state_root, hosts, *, user_home=None, appdata=None):
    bundle, state_root = Path(bundle).resolve(), Path(state_root).resolve()
    user_home = Path(user_home or Path.home()).resolve()
    appdata = Path(appdata or os.environ.get("APPDATA", user_home / "AppData/Roaming")).resolve()
    hosts = list(dict.fromkeys("openai" if h == "codex" else h for h in hosts))
    if set(hosts) - {"claude", "workbuddy", "openai", "codex-direct"}:
        raise ValueError("Supported hosts: openai, claude, workbuddy, codex-direct")
    executable = bundle / "server/origin-agent.exe"
    manifest = read_json(bundle / "manifest.json")
    if manifest["version"] != __version__ or not executable.is_file():
        raise ValueError("Bundle version or executable is invalid")
    entry = {
        "type": "stdio",
        "command": str(executable),
        "args": ["serve"],
        "env": {"ORIGIN_AGENT_HOME": str(state_root)},
    }
    plans = []
    destinations = {
        "claude": appdata / "Claude/claude_desktop_config.json",
        "workbuddy": user_home / ".workbuddy/mcp.json",
    }
    for host in hosts:
        if host in destinations:
            target = destinations[host]
            plans.append((target, host_config(target, entry)))
        if host in ("workbuddy", "codex-direct"):
            skill_root = user_home / (".workbuddy/skills" if host == "workbuddy" else ".agents/skills")
            for source in sorted((bundle / "skills").rglob("*")):
                if source.is_file():
                    plans.append((skill_root / source.relative_to(bundle / "skills"), source.read_bytes()))
    for host in ("claude", "workbuddy", "generic-mcp"):
        plans.append(
            (
                state_root / f"host-configs/{__version__}/{host}.json",
                encoded({"mcpServers": {"origin-agent": entry}}),
            )
        )
    plans.append(
        (
            state_root / "install.json",
            encoded({"version": __version__, "root": str(bundle), "executable": str(executable)}),
        )
    )
    changes = Changes(state_root)
    try:
        for path, data in plans[:-1]:
            changes.put(path, data)
        if "codex-direct" in hosts:
            if user_home != Path.home().resolve() or os.environ.get("CODEX_HOME"):
                raise ValueError("Codex automatic setup requires its default user profile")
            changes.codex(executable, state_root, user_home)
        # The installation pointer changes only after all selected host configurations succeed.
        changes.put(*plans[-1])
        changes.value.update(status="installed", version=__version__, hosts=hosts, bundle=str(bundle))
        changes.save()
    except Exception:
        rollback(state_root, changes.root.name)
        raise
    return {
        "version": __version__,
        "hosts": hosts,
        "receipt_id": changes.root.name,
        "executable": str(executable),
        "restart_hosts": True,
        "chatgpt": "Use Connect-OpenAI.cmd for the same registered plugin in Chat, Work and Codex. "
        "Existing tunnel configuration is preserved; reconnect to load the new engine.",
    }


def doctor(store, native=False):
    from .discovery import discover

    result = {"plugin_version": __version__, **discover(), "native_tested": False}
    if native:
        import time

        from .jobs import cancel, get_job, submit
        from .programs import OriginProgram, prepare_program
        from .storage import Store

        probe = Store(store.root / "verification" / uuid.uuid4().hex)
        program = OriginProgram(
            title="Installation self-check",
            language="python",
            graph_formats=[],
            code="w=op.new_sheet('w'); w.from_list(0,[1,2,3]); "
            "assert w.to_list(0)==[1,2,3]; RESULTS['native_readback']=True",
        )
        prepared = prepare_program(probe, program)
        job = submit(probe, prepared["plan_id"], expected_kind="program")
        deadline = time.monotonic() + 90
        while job["state"] not in ("succeeded", "failed", "cancelled", "interrupted"):
            if time.monotonic() > deadline:
                cancel(probe, job["job_id"])
                raise TimeoutError(
                    "Origin self-check timed out; finish any active Origin Companion session and retry"
                )
            time.sleep(0.2)
            job = get_job(probe, job["job_id"])
        if job["state"] != "succeeded":
            raise RuntimeError(f"Origin self-check failed: {job.get('error')}")
        result.update(
            native_tested=True,
            native_readback=True,
            verification=str(probe.root),
            engine=read_json(probe.path("jobs", job["job_id"]) / "manifest.json")["engine"],
        )
    return result
