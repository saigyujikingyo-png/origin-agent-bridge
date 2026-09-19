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


def rollback(state_root, receipt_id, *, defer_activation=False):
    from . import tunnel_install
    from .lifecycle_admission import transaction

    valid_id(receipt_id)
    state_root = Path(state_root).resolve()
    with transaction(state_root, receipt_id, recovery=True):
        result = _rollback(state_root, receipt_id)
    if not defer_activation:
        tunnel_install.activate_rollback(state_root, receipt_id)
    return result


def _rollback(state_root, receipt_id):
    from . import tunnel_install
    from .lifecycle_admission import intent_guard

    valid_id(receipt_id)
    root = Path(state_root) / "installations" / receipt_id
    path = root / "receipt.json"
    receipt = read_json(path)
    if receipt.get("files") or receipt.get("tasks"):
        tunnel_install.check_activation_pending(state_root, receipt_id=receipt_id)
    if receipt["status"] == "rolled_back":
        return {"receipt_id": receipt_id, "status": "rolled_back"}
    # Check every file before changing any; never overwrite edits made after installation.
    restore = []
    for item in receipt["files"]:
        # Starting/stopping a connector is a live user preference, not a later
        # source/config edit. Completed rollback preserves that current preference.
        if receipt["status"] == "installed" and item.get("lifecycle_intent"):
            continue
        target = Path(item["path"])
        current = digest(contents(target))
        if current == item["before"] and not item.get("lifecycle_intent"):
            continue
        if current not in tunnel_install.intent_states(item):
            raise RuntimeError(f"Rollback conflict; file changed since installation: {target}")
        backup = item["backup"]
        data = contents(root / Path(backup).name) if backup else None
        if digest(data) != item["before"]:
            raise RuntimeError("Installation backup failed integrity verification")
        restore.append((target, data, item))
    tasks, task_restore = tunnel_install.prepare_task_rollback(receipt, root)
    tunnel_intents = tunnel_install.quiesce_rollback(receipt, root, tasks)
    for target, data, item in reversed(restore):
        if item.get("lifecycle_intent"):
            with intent_guard(target.parent):
                _restore_file(target, data, item)
        else:
            _restore_file(target, data, item)
    tunnel_install.restore_rollback_intents(receipt, root, tunnel_intents)
    tunnel_install.restore_tasks(tasks, task_restore, receipt, root)
    receipt["status"] = "rolled_back"
    write_json(path, receipt)
    return {"receipt_id": receipt_id, "status": "rolled_back", "restored_files": len(restore)}


def _restore_file(target, data, item):
    from .tunnel_install import intent_states

    current = digest(contents(target))
    if current not in intent_states(item):
        raise RuntimeError(f"Rollback conflict; file changed during recovery: {target}")
    if data is None:
        target.unlink(missing_ok=True)
    else:
        atomic_bytes(target, data)


def integrate(bundle, state_root, hosts, *, user_home=None, appdata=None):
    from . import tunnel_install
    from .lifecycle_admission import transaction

    state_root = Path(state_root).resolve()
    # Only a unique private receipt is allocated before admission. All shared
    # configuration reads/planning and publication belong to the one transaction.
    changes = Changes(state_root)
    failure = None
    with transaction(state_root, changes.root.name):
        try:
            tunnel_install.check_activation_pending(state_root)
            result = _integrate(bundle, state_root, hosts, changes, user_home=user_home, appdata=appdata)
        except Exception as exc:
            rollback(state_root, changes.root.name, defer_activation=True)
            failure = exc
    if failure is not None:
        tunnel_install.activate_rollback(state_root, changes.root.name)
        raise failure
    return result


def _integrate(bundle, state_root, hosts, changes, *, user_home=None, appdata=None):
    from . import tunnel_install

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
    # Reconcile all account scopes before changing a launcher or active engine.
    # Migration preserves task preferences and never starts a connector.
    private_tunnels = tunnel_install.migrate(changes, bundle, state_root)
    for path, data in plans[:-1]:
        changes.put(path, data)
    if "codex-direct" in hosts:
        if user_home != Path.home().resolve() or os.environ.get("CODEX_HOME"):
            raise ValueError("Codex automatic setup requires its default user profile")
        changes.codex(executable, state_root, user_home)
    # The installation pointer changes only after all selected host configurations succeed.
    changes.put(*plans[-1])
    tunnel_install.finish_migration(changes)
    changes.value.update(status="installed", version=__version__, hosts=hosts, bundle=str(bundle))
    changes.save()
    return {
        "version": __version__,
        "hosts": hosts,
        "receipt_id": changes.root.name,
        "executable": str(executable),
        "restart_hosts": True,
        "private_tunnels": private_tunnels,
        "chatgpt": "Use Connect-OpenAI.cmd for the same registered plugin in Chat, Work and Codex. "
        "Private account identities and startup preferences are preserved. "
        "Start the private connector explicitly after upgrade; installation does not start it.",
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
