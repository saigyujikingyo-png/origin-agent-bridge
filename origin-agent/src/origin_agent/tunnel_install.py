"""Source-owned, reversible startup configuration for private account connectors.

This module never reads plaintext keys and never starts a connector during an
engine upgrade. Native jobs and host-owned MCP processes belong to other owners.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from .installation import atomic_bytes, contents, digest, encoded
from .storage import file_lock, write_json

TASK_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
SCRIPTS = ("Run-ChatGPT-Tunnel.ps1", "Stop-ChatGPT-Tunnel.ps1")
ALIAS = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}\Z")


def canonical(path):
    return os.path.normcase(str(Path(path).resolve()))


def lifecycle_api():
    from . import tunnel_lifecycle

    return tunnel_lifecycle


def task_xml(record):
    def node(parent, name, value=None):
        child = ET.SubElement(parent, name)
        if value is not None:
            child.text = str(value)
        return child

    task = ET.Element("Task", {"version": "1.2", "xmlns": TASK_NS})
    registration = node(task, "RegistrationInfo")
    node(registration, "Description", "Origin Companion private connector; owned account scope only.")
    triggers = node(task, "Triggers")
    trigger = node(triggers, "LogonTrigger")
    node(trigger, "Enabled", "true")
    node(trigger, "UserId", record["user_sid"])
    principals = node(task, "Principals")
    principal = node(principals, "Principal")
    principal.set("id", "Owner")
    node(principal, "UserId", record["user_sid"])
    node(principal, "LogonType", "InteractiveToken")
    node(principal, "RunLevel", "LeastPrivilege")
    settings = node(task, "Settings")
    for name, value in (
        ("MultipleInstancesPolicy", "IgnoreNew"),
        ("DisallowStartIfOnBatteries", "false"),
        ("StopIfGoingOnBatteries", "false"),
        ("AllowHardTerminate", "false"),
        ("StartWhenAvailable", "true"),
        ("Enabled", str(record["enabled"]).lower()),
        ("ExecutionTimeLimit", "PT0S"),
    ):
        node(settings, name, value)
    restart = node(settings, "RestartOnFailure")
    node(restart, "Interval", "PT1M")
    node(restart, "Count", 3)
    actions = node(task, "Actions")
    actions.set("Context", "Owner")
    for action in record["actions"]:
        command = node(actions, "Exec")
        node(command, "Command", action["execute"])
        node(command, "Arguments", action["arguments"])
        node(command, "WorkingDirectory", action["working_directory"])
    return ET.tostring(task, encoding="unicode")


def record_from_xml(name, path, xml):
    tree = ET.fromstring(xml)
    ns = {"t": TASK_NS}
    return {
        "name": name,
        "path": path,
        "xml": xml,
        "user_sid": tree.findtext("t:Principals/t:Principal/t:UserId", namespaces=ns),
        "enabled": tree.findtext("t:Settings/t:Enabled", "true", ns).lower() == "true",
        "actions": [
            {
                "execute": action.findtext("t:Command", "", ns),
                "arguments": action.findtext("t:Arguments", "", ns),
                "working_directory": action.findtext("t:WorkingDirectory", "", ns),
            }
            for action in tree.findall("t:Actions/t:Exec", ns)
        ],
    }


_TASK_DRIVER = r"""
$ErrorActionPreference = 'Stop'
Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Management\Microsoft.PowerShell.Management.psd1')
Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1')
Import-Module ($PSHOME + '\Modules\CimCmdlets\CimCmdlets.psd1')
Import-Module ($PSHOME + '\Modules\ScheduledTasks\ScheduledTasks.psd1')
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
$request = [Console]::In.ReadToEnd() | ConvertFrom-Json
function Read-Task($name, $path) {
    $found = @(Get-ScheduledTask | Where-Object { $_.TaskName -ceq $name -and $_.TaskPath -ceq $path })
    if ($found.Count -gt 1) { throw 'Ambiguous scheduled task identity.' }
    if ($found.Count -eq 1) { return $found[0] }
    return $null
}
function Describe-Task($task) {
    if (-not $task) { return $null }
    $sid = $task.Principal.UserId
    if ($sid -notmatch '^S-1-') {
        try {
            $sid = ([Security.Principal.NTAccount]$sid).Translate(
                [Security.Principal.SecurityIdentifier]).Value
        }
        catch { $sid = 'unresolved' }
    }
    [pscustomobject]@{
        name=$task.TaskName; path=$task.TaskPath; user_sid=$sid; enabled=[bool]$task.Settings.Enabled
        xml=(Export-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath)
        actions=@($task.Actions | ForEach-Object {
            [pscustomobject]@{
                execute=$_.Execute; arguments=$_.Arguments; working_directory=$_.WorkingDirectory
            }
        })
    }
}
$result = $null
switch ($request.operation) {
    'list' {
        $items = @(Get-ScheduledTask | Where-Object {
            $_.TaskName -like 'Origin Companion Private Tunnel*' -or
            @($_.Actions | Where-Object { $_.Arguments -like '*Run-ChatGPT-Tunnel.ps1*' }).Count -gt 0
        })
        $result = [pscustomobject]@{
            user_sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
            powershell=(Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe')
            tasks=@($items | ForEach-Object { Describe-Task $_ })
        }
    }
    'read' { $result = Describe-Task (Read-Task $request.name $request.path) }
    'register' {
        $registration = @{ TaskName=$request.name; TaskPath=$request.path; Xml=$request.xml; Force=$true }
        Register-ScheduledTask @registration | Out-Null
        $result = Describe-Task (Read-Task $request.name $request.path)
    }
    'disable' {
        $task = Read-Task $request.name $request.path
        if (-not $task) { throw 'The owned scheduled task disappeared.' }
        Disable-ScheduledTask -InputObject $task | Out-Null
        $result = Describe-Task (Read-Task $request.name $request.path)
    }
    'remove' {
        $task = Read-Task $request.name $request.path
        if ($task) { Unregister-ScheduledTask -InputObject $task -Confirm:$false }
    }
    'start' {
        $task = Read-Task $request.name $request.path
        if (-not $task -or -not $task.Settings.Enabled) {
            throw 'The owned startup task is disabled or missing.'
        }
        Start-ScheduledTask -InputObject $task
    }
    default { throw 'Unsupported startup operation.' }
}
ConvertTo-Json -InputObject $result -Depth 12 -Compress
"""


class WindowsTasks:
    """Bounded Task Scheduler adapter. Arguments/data never become shell code."""

    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("Windows Task Scheduler is required to migrate configured private tunnels")
        self.powershell = str(
            Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        )
        initial = self._call("list")
        self.user_sid = initial["user_sid"]
        self.powershell = initial["powershell"]

    def _call(self, operation, **data):
        result = subprocess.run(
            [self.powershell, "-NoProfile", "-NonInteractive", "-Command", _TASK_DRIVER],
            input=json.dumps({"operation": operation, **data}),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=30,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode or len(result.stdout) > 2 * 1024 * 1024:
            raise RuntimeError(f"Task Scheduler {operation} failed; no unverified task is trusted")
        return json.loads(result.stdout)

    def list(self):
        return self._call("list")["tasks"]

    def read(self, name, path="\\"):
        return self._call("read", name=name, path=path)

    def register(self, record):
        self._call("register", name=record["name"], path=record["path"], xml=record["xml"])

    def disable(self, name, path="\\"):
        self._call("disable", name=name, path=path)

    def restore(self, name, path, xml):
        if xml is None:
            self._call("remove", name=name, path=path)
        else:
            self._call("register", name=name, path=path, xml=xml)

    def start(self, name, path="\\"):
        self._call("start", name=name, path=path)


def launcher_arguments(cloud_root):
    return (
        '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "'
        + str(Path(cloud_root) / "Run-ChatGPT-Tunnel.ps1")
        + '"'
    )


def new_task(alias, cloud_root, state_root, tasks, *, enabled=False):
    scope = hashlib.sha256(canonical(cloud_root).encode()).hexdigest()[:12]
    record = {
        "name": f"Origin Companion Private Tunnel-{alias}-{scope}-{tasks.user_sid}",
        "path": "\\",
        "user_sid": tasks.user_sid,
        "enabled": enabled,
        "actions": [
            {
                "execute": tasks.powershell,
                "arguments": launcher_arguments(cloud_root),
                "working_directory": str(state_root),
            }
        ],
    }
    record["xml"] = task_xml(record)
    return record


def _action_scope(record, cloud_root):
    actions = record.get("actions", [])
    if len(actions) != 1:
        return False
    match = re.fullmatch(
        r'-NoProfile\s+-NonInteractive\s+-WindowStyle\s+Hidden\s+-ExecutionPolicy\s+Bypass\s+-File\s+"([^"\r\n]+)"',
        actions[0].get("arguments", ""),
        re.IGNORECASE,
    )
    return bool(match and canonical(match[1]) == canonical(Path(cloud_root) / "Run-ChatGPT-Tunnel.ps1"))


def _references_scope(record, cloud_root):
    # A malformed/multi-action task that mentions the exact launcher could still
    # respawn the old wrapper; fail closed rather than silently creating another.
    if _action_scope(record, cloud_root):
        return True
    wanted = canonical(Path(cloud_root) / "Run-ChatGPT-Tunnel.ps1").replace("/", "\\").casefold()
    return any(
        wanted in str(action.get("arguments", "")).replace("/", "\\").casefold()
        for action in record.get("actions", [])
    )


def _owned_task(record, cloud_root, tasks):
    return (
        _action_scope(record, cloud_root)
        and record["user_sid"] == tasks.user_sid
        and canonical(record["actions"][0]["execute"]) == canonical(tasks.powershell)
    )


def _inside(path, parent):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(Path(parent).resolve()):
        raise ValueError("Private tunnel path escapes its canonical state directory")
    return resolved


def discover(state_root):
    """Return configs without exposing profile contents, keys or tunnel identifiers."""
    state_root = Path(state_root).resolve()
    cloud = state_root / "cloud"
    roots = [cloud]
    accounts = cloud / "accounts"
    if accounts.is_dir():
        roots.extend(sorted(path for path in accounts.iterdir() if path.is_dir()))
    result, seen = [], set()
    for root in roots:
        directory = _inside(root / "profiles", state_root)
        profiles = sorted(directory.glob("*.yaml")) if directory.is_dir() else []
        if not profiles:
            continue
        if len(profiles) != 1:
            raise ValueError("Each account directory must contain exactly one managed profile")
        root = _inside(root, state_root)
        if canonical(directory) in seen:
            raise ValueError("Ambiguous canonical private tunnel profile directory")
        seen.add(canonical(directory))
        source = _inside(profiles[0], directory)
        alias = source.stem
        if not ALIAS.fullmatch(alias):
            raise ValueError("Invalid private tunnel profile name")
        try:
            profile = json.loads(source.read_text(encoding="utf-8-sig"))
            plane = profile["control_plane"]
            if not re.fullmatch(r"tunnel_[a-f0-9]+", plane["tunnel_id"]):
                raise ValueError
            if plane["api_key"] != "env:CONTROL_PLANE_API_KEY":
                raise ValueError
        except (ValueError, TypeError, KeyError):
            raise ValueError(
                "A managed JSON-compatible profile with an environment key reference is required"
            ) from None
        existing = root / "runtime-config.json"
        saved = json.loads(existing.read_text(encoding="utf-8-sig")) if existing.is_file() else {}
        secret = (
            root / "runtime-key.dpapi" if root != cloud.resolve() else state_root / "secrets/tunnel-key.dpapi"
        )
        secret = _inside(saved.get("secret_file", secret), state_root)
        client = Path(
            saved.get("tunnel_client", state_root / "tunnel-client/v0.0.14/tunnel-client.exe")
        ).resolve()
        if not secret.is_file() or not client.is_file():
            raise ValueError("The existing encrypted runtime key or tunnel client is missing")
        config = {
            "schema_version": 1,
            "alias": saved.get("alias", alias),
            "profile": alias,
            "profile_dir": str(directory),
            "cloud_root": str(root),
            "state_root": str(state_root),
            "secret_file": str(secret),
            "tunnel_client": str(client),
        }
        if not isinstance(config["alias"], str) or not ALIAS.fullmatch(config["alias"]):
            raise ValueError("Invalid private tunnel alias")
        for key in ("profile", "profile_dir", "cloud_root", "state_root"):
            if key in saved and saved[key] != config[key]:
                raise ValueError("Existing private tunnel configuration has conflicting scope")
        result.append(config)
    if len({c["alias"] for c in result}) != len(result):
        raise ValueError("Ambiguous private tunnel aliases across account directories")
    return result


def _task_hash(record):
    return digest(record["xml"].encode("utf-8")) if record else None


def _xml_policy(xml, *, ignore_enabled=False):
    tree = ET.fromstring(xml)
    if ignore_enabled:
        enabled = tree.find(f"{{{TASK_NS}}}Settings/{{{TASK_NS}}}Enabled")
        if enabled is not None:
            enabled.text = "preference"
    return ET.canonicalize(ET.tostring(tree, encoding="unicode"), strip_text=True, rewrite_prefixes=True)


def _task_after(root, receipt, item, record):
    item["after"] = _task_hash(record)
    item["after_backup"] = None
    if record:
        item["after_backup"] = f"task-{receipt['tasks'].index(item)}-after.xml"
        atomic_bytes(root / item["after_backup"], record["xml"].encode("utf-8"))
    write_json(root / "receipt.json", receipt)


def _capture_task(changes, tasks, record):
    path, name = record["path"], record["name"]
    before = tasks.read(name, path)
    entries = changes.value.setdefault("tasks", [])
    backup = f"task-{len(entries)}.xml" if before else None
    if backup:
        atomic_bytes(changes.root / backup, before["xml"].encode("utf-8"))
    item = {
        "name": name,
        "path": path,
        "before": _task_hash(before),
        "after": _task_hash(before),
        "backup": backup,
        "after_backup": backup,
    }
    entries.append(item)
    changes.save()
    return item


def _change_task(changes, tasks, item, action):
    if _task_hash(tasks.read(item["name"], item["path"])) != item["after"]:
        raise RuntimeError("Scheduled task changed during installation")
    try:
        action()
    finally:
        # Preserve the actual after-state even when a scheduler write returned an error.
        _task_after(changes.root, changes.value, item, tasks.read(item["name"], item["path"]))


def _intent_snapshot(changes, path):
    before = contents(path)
    item = changes.prepare(path, before)
    item["lifecycle_intent"] = True
    changes.save()
    return path, before, item


def _observe_intent(changes, snapshot):
    path, _, item = snapshot
    item["after"] = digest(contents(path))
    changes.save()


def _restore_intent(changes, snapshot):
    path, before, item = snapshot
    if digest(contents(path)) != item["after"]:
        raise RuntimeError("Private tunnel intent changed during installation")
    if before is None:
        path.unlink(missing_ok=True)
    else:
        atomic_bytes(path, before)
    item["after"] = digest(before)
    changes.save()


def migrate(changes, bundle, state_root, *, enable_new=False):
    """Quiesce every configured scope before changing launchers or the engine pointer."""
    configs = discover(state_root)
    if not configs:
        return []
    state_root, bundle = Path(state_root).resolve(), Path(bundle).resolve()
    if not (state_root / "install.json").is_file():
        raise RuntimeError("An installed engine pointer is required before private tunnel migration")
    for name in SCRIPTS:
        if not (bundle / name).is_file():
            raise ValueError("The release does not contain the private tunnel lifecycle scripts")
    tasks, api = WindowsTasks(), lifecycle_api()
    observed = tasks.list()
    plans = []
    for config in configs:
        root = Path(config["cloud_root"])
        matches = [task for task in observed if _references_scope(task, root)]
        if len(matches) > 1:
            raise RuntimeError("Ambiguous startup tasks for one private tunnel scope")
        if matches and not _owned_task(matches[0], root, tasks):
            raise RuntimeError("Private tunnel startup task ownership is unproven")
        existing = matches[0] if matches else None
        record = new_task(
            config["alias"], root, state_root, tasks, enabled=existing["enabled"] if existing else enable_new
        )
        if existing:
            record.update(name=existing["name"], path=existing["path"])
        elif tasks.read(record["name"], record["path"]) is not None:
            raise RuntimeError("An unrelated startup task occupies the generated name")
        config["task_name"] = record["name"]
        config["task_path"] = record["path"]
        record["xml"] = task_xml(record)
        plans.append((config, record, existing))
    changes.value["lifecycle"] = {
        "schema_version": 1,
        "configs": configs,
        "auto_started": False,
        "phase": "preparing",
    }
    changes.save()
    snapshots, task_items = [], []
    # Disable all exact registrations before quiescing any scope. Never terminate a task tree.
    for _config, record, existing in plans:
        item = _capture_task(changes, tasks, record)
        task_items.append(item)
        if existing:
            _change_task(changes, tasks, item, lambda r=record: tasks.disable(r["name"], r["path"]))
    for index, (config, _, _) in enumerate(plans):
        snapshot = _intent_snapshot(changes, Path(config["cloud_root"]) / "intent.json")
        snapshots.append(snapshot)
        candidate = changes.root / f"tunnel-config-{index}.json"
        atomic_bytes(candidate, encoded(config))
        try:
            stopped = api.stop(candidate, disable=False)
            if stopped.get("state") != "stopped":
                raise RuntimeError("Private tunnel shutdown is not confirmed; installation did not switch")
        finally:
            _observe_intent(changes, snapshot)
    # From this point on a supported concurrent start may observe published files.
    # Every subsequent rollback reconciles again, even if the installer never starts.
    changes.value["lifecycle"]["phase"] = "publishing"
    changes.save()
    for (config, record, _), item in zip(plans, task_items, strict=True):
        root = Path(config["cloud_root"])
        changes.put(root / "runtime-config.json", encoded(config))
        for name in SCRIPTS:
            changes.put(root / name, (bundle / name).read_bytes())
        disabled = dict(record, enabled=False)
        disabled["xml"] = task_xml(disabled)
        _change_task(changes, tasks, item, lambda r=disabled: tasks.register(r))
        actual = tasks.read(record["name"], record["path"])
        if not actual or not _owned_task(actual, root, tasks) or actual["enabled"]:
            raise RuntimeError("Private tunnel startup registration readback did not match")
    # This object is deliberately process-local, not serialized into the receipt.
    # Stop intent and disabled registrations bridge the gap until install.json commits.
    changes.tunnel_transition = (plans, tasks, api, task_items, snapshots)
    changes.value["lifecycle"]["phase"] = "published"
    changes.save()
    return [
        {
            "alias": c["alias"],
            "config": str(Path(c["cloud_root"]) / "runtime-config.json"),
            "startup_enabled": r["enabled"],
            "started": False,
        }
        for c, r, _ in plans
    ]


def finish_migration(changes, *, start_now=False):
    transition = getattr(changes, "tunnel_transition", None)
    if transition is None:
        return
    plans, tasks, api, task_items, snapshots = transition
    for (_config, record, _), item in zip(plans, task_items, strict=True):
        _change_task(changes, tasks, item, lambda r=record: tasks.register(r))
        actual = tasks.read(record["name"], record["path"])
        if not actual or actual["enabled"] != record["enabled"]:
            raise RuntimeError("Private tunnel startup preference readback did not match")
    for snapshot in snapshots:
        _restore_intent(changes, snapshot)
    if start_now:
        # Clearing explicit stop can permit a contemporaneous logon trigger too.
        changes.value["lifecycle"]["auto_started"] = True
        changes.save()
        for (config, record, _), item, snapshot in zip(plans, task_items, snapshots, strict=True):
            try:
                api.allow_start(Path(config["cloud_root"]) / "runtime-config.json")
            finally:
                _observe_intent(changes, snapshot)
            record["enabled"] = True
            record["xml"] = task_xml(record)
            _change_task(changes, tasks, item, lambda r=record: tasks.register(r))
            tasks.start(record["name"], record["path"])


def prepare_task_rollback(receipt, root):
    entries = receipt.get("tasks", [])
    if not entries:
        return None, []
    tasks, plans = WindowsTasks(), []
    for item in entries:
        record = tasks.read(item["name"], item["path"])
        current = _task_hash(record)
        if current not in (item["before"], item["after"]):
            after_backup = item.get("after_backup")
            after = contents(root / Path(after_backup).name) if after_backup else None
            same_policy = (
                receipt["status"] == "installed"
                and record
                and after
                and digest(after) == item["after"]
                and _xml_policy(record["xml"], ignore_enabled=True)
                == _xml_policy(after.decode("utf-8"), ignore_enabled=True)
            )
            if not same_policy:
                raise RuntimeError("Rollback conflict; startup task changed since installation")
        if receipt["status"] == "installed" and record:
            item.setdefault("rollback_enabled", record["enabled"])
            # Preserve only the enabled/disabled preference; all other edits still conflict.
            _task_after(root, receipt, item, record)
        backup = item["backup"]
        raw = contents(root / Path(backup).name) if backup else None
        if digest(raw) != item["before"]:
            raise RuntimeError("Startup task backup failed integrity verification")
        xml = raw.decode("utf-8") if raw else None
        if xml and "rollback_enabled" in item:
            tree = ET.fromstring(xml)
            enabled = tree.find(f"{{{TASK_NS}}}Settings/{{{TASK_NS}}}Enabled")
            if enabled is None:
                raise RuntimeError("Startup task preference cannot be safely restored")
            if enabled.text.lower() != str(item["rollback_enabled"]).lower():
                enabled.text = str(item["rollback_enabled"]).lower()
                xml = ET.tostring(tree, encoding="unicode")
        plans.append((item, xml))
    return tasks, plans


def quiesce_rollback(receipt, root, tasks):
    # Preparing/failed upgrades already quiesced before switching any lifecycle files.
    # A completed install may have subsequently been started by the user.
    lifecycle = receipt.get("lifecycle")
    if not lifecycle or (
        receipt["status"] != "installed"
        and not lifecycle.get("auto_started")
        and lifecycle.get("phase") not in ("publishing", "published")
    ):
        return []
    preserve_preference = receipt["status"] == "installed"
    api = lifecycle_api()
    for config in receipt["lifecycle"]["configs"]:
        task = tasks.read(config["task_name"], config.get("task_path", "\\"))
        if task:
            item = next(
                t for t in receipt["tasks"] if t["name"] == task["name"] and t["path"] == task["path"]
            )
            if _task_hash(task) not in (item["before"], item["after"]):
                raise RuntimeError("Rollback conflict; startup task changed during shutdown")
            if not _owned_task(task, config["cloud_root"], tasks):
                raise RuntimeError("Rollback startup task ownership is unproven")
            try:
                tasks.disable(task["name"], task["path"])
            finally:
                _task_after(root, receipt, item, tasks.read(task["name"], task["path"]))
        candidate = root / ("rollback-" + config["alias"] + ".json")
        atomic_bytes(candidate, encoded(config))
        intent = Path(config["cloud_root"]) / "intent.json"
        if preserve_preference:
            saved = receipt.setdefault("rollback_intents", [])
            snapshot = next((value for value in saved if value["path"] == str(intent)), None)
            if snapshot is None:
                before = contents(intent)
                backup = f"rollback-intent-{len(saved)}.bin" if before is not None else None
                if backup:
                    atomic_bytes(root / backup, before)
                snapshot = {
                    "path": str(intent),
                    "before": digest(before),
                    "after": digest(before),
                    "backup": backup,
                }
                saved.append(snapshot)
                write_json(root / "receipt.json", receipt)
            elif digest(contents(intent)) != snapshot["after"]:
                raise RuntimeError("Rollback conflict; private tunnel intent changed during recovery")
        else:
            snapshot = next(value for value in receipt["files"] if value["path"] == str(intent.resolve()))
        try:
            stopped = api.stop(candidate, disable=False)
            if stopped.get("state") != "stopped":
                raise RuntimeError("Private tunnel rollback shutdown is not confirmed")
        finally:
            snapshot["after"] = digest(contents(intent))
            write_json(root / "receipt.json", receipt)
    return receipt.get("rollback_intents", [])


def restore_rollback_intents(receipt, root, snapshots):
    for item in snapshots:
        target = Path(item["path"])
        if digest(contents(target)) != item["after"]:
            raise RuntimeError("Rollback conflict; private tunnel intent changed during recovery")
        before = contents(root / Path(item["backup"]).name) if item["backup"] else None
        if digest(before) != item["before"]:
            raise RuntimeError("Private tunnel intent backup failed integrity verification")
        if before is None:
            target.unlink(missing_ok=True)
        else:
            atomic_bytes(target, before)
        item["after"] = digest(before)
        write_json(root / "receipt.json", receipt)


def restore_tasks(tasks, plans, receipt, root):
    if tasks is None:
        return
    for item, xml in reversed(plans):
        record = tasks.read(item["name"], item["path"])
        current = _task_hash(record)
        if (not record and xml is None) or (
            record and xml and _xml_policy(record["xml"]) == _xml_policy(xml)
        ):
            continue
        if current not in (item["before"], item["after"]):
            raise RuntimeError("Rollback conflict; startup task changed during recovery")
        tasks.restore(item["name"], item["path"], xml)
        actual = tasks.read(item["name"], item["path"])
        _task_after(root, receipt, item, actual)
        if (xml is None and actual) or (
            xml and (not actual or _xml_policy(actual["xml"]) != _xml_policy(xml))
        ):
            raise RuntimeError("Startup task rollback readback failed")


def install_startup(state_root, *, profile_source=None, start_now=False):
    """Explicit setup entrypoint; reuse credentials and profile IDs, never re-key."""
    from .installation import Changes, rollback

    state_root = Path(state_root).resolve()
    install = json.loads((state_root / "install.json").read_text(encoding="utf-8-sig"))
    changes = Changes(state_root)
    try:
        if profile_source:
            destination = state_root / "cloud/profiles/origin-agent.yaml"
            if not destination.exists():
                changes.put(destination, Path(profile_source).read_bytes())
        result = migrate(changes, Path(install["root"]), state_root, enable_new=True)
        if not result:
            raise ValueError("Set up an existing private tunnel profile and encrypted key first")
        finish_migration(changes, start_now=start_now)
        if start_now:
            for item in result:
                item.update(started=True, startup_enabled=True)
        changes.value.update(status="installed", kind="startup", version=install["version"])
        changes.save()
    except Exception:
        rollback(state_root, changes.root.name)
        raise
    return {"status": "configured", "receipt_id": changes.root.name, "profiles": result}


def disable_startup(config_path):
    config = json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
    tasks = WindowsTasks()
    matches = [task for task in tasks.list() if _references_scope(task, config["cloud_root"])]
    if len(matches) > 1 or (matches and not _owned_task(matches[0], config["cloud_root"], tasks)):
        raise RuntimeError("Private tunnel startup task ownership is ambiguous")
    if matches:
        task = matches[0]
        tasks.disable(task["name"], task["path"])
        if tasks.read(task["name"], task["path"])["enabled"]:
            raise RuntimeError("Private tunnel startup disable was not confirmed")
    return {"startup_enabled": False}


def initialize_profile(state_root, tunnel_id, tunnel_client):
    """Initialize once under the runtime's canonical lock; never replace a profile.

    The vendor generates into a private staging directory. A verified profile is
    published with an exclusive hard link, so even a non-cooperating writer cannot
    be overwritten between the preflight and final publication.
    """
    from .tunnel_lifecycle import Connection, Controller
    from .tunnel_lifecycle import canonical as runtime_canonical

    if not re.fullmatch(r"tunnel_[a-f0-9]+", tunnel_id):
        raise ValueError("A valid private tunnel identifier is required")
    state_root = Path(state_root).resolve()
    selected = shutil.which(str(tunnel_client)) if not Path(tunnel_client).is_absolute() else tunnel_client
    if not selected or not Path(selected).is_file():
        raise ValueError("The official tunnel client executable was not found")
    client = Path(selected).resolve()
    cloud = _inside(state_root / "cloud", state_root)
    profile_dir = _inside(cloud / "profiles", cloud)
    connection = Connection(
        alias="origin-agent",
        profile="origin-agent",
        profile_dir=profile_dir,
        cloud_root=cloud,
        state_root=state_root,
        secret_file=state_root / "secrets/tunnel-key.dpapi",
        tunnel_client=client,
    )
    if not connection.engine.is_file():
        raise ValueError("Install Origin Companion before initializing a private connector")
    with file_lock(connection.lock, timeout=0):
        if connection.profile_path.exists():
            raise RuntimeError("Existing private tunnel profile preserved; use the managed start entrypoint")
        controller = Controller(connection)
        daemons, frontends = controller.scan()
        if daemons or frontends:
            raise RuntimeError("A private connector owner already exists; reconcile it before initialization")
        tasks = WindowsTasks()
        if any(_references_scope(task, cloud) for task in tasks.list()):
            raise RuntimeError("Existing private startup registration preserved; use migration instead")
        # Legacy PowerShell wrappers do not hold the new scope lock. Refuse one
        # even if its account profile has disappeared; do not create under it.
        import psutil

        launcher = runtime_canonical(cloud / "Run-ChatGPT-Tunnel.ps1")
        for process in psutil.process_iter(["cmdline"]):
            try:
                for arg in process.info["cmdline"] or []:
                    try:
                        matches = runtime_canonical(arg) == launcher
                    except (OSError, ValueError):
                        continue
                    if matches:
                        raise RuntimeError("A legacy private connector launcher is still active")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        stage_root = _inside(cloud / "setup", cloud)
        stage_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="profile-", dir=stage_root) as stage:
            stage = _inside(stage, stage_root)
            result = subprocess.run(
                [
                    str(client),
                    "init",
                    "--sample",
                    "sample_mcp_stdio_local",
                    "--profile",
                    "origin-agent",
                    "--profile-dir",
                    str(stage),
                    "--tunnel-id",
                    tunnel_id,
                    "--mcp-command",
                    f'"{connection.engine.as_posix()}" serve',
                ],
                capture_output=True,
                timeout=30,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode:
                raise RuntimeError("Private tunnel initialization failed; existing profiles were preserved")
            generated = stage / "origin-agent.yaml"
            if not generated.is_file() or generated.stat().st_size > 1024 * 1024:
                raise RuntimeError("Private tunnel initialization did not produce a bounded managed profile")
            raw = generated.read_bytes()
            try:
                value = json.loads(raw.decode("utf-8-sig"))["control_plane"]
                valid = value["tunnel_id"] == tunnel_id and value["api_key"] == "env:CONTROL_PLANE_API_KEY"
            except (ValueError, TypeError, KeyError):
                valid = False
            if not valid:
                raise RuntimeError("Generated private profile failed identity or key-reference validation")
            # Refuse filesystems without safe exclusive publication; never use an
            # overwrite fallback for account identity configuration.
            os.link(generated, connection.profile_path)
    return {
        "state": "initialized",
        "profile": "origin-agent",
        "profile_dir": str(profile_dir),
        "started": False,
    }
