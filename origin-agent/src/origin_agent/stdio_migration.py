"""Private, hash-guarded host configuration staging and rollback.

No process control. The maintenance owner must first verify a host-safe checkpoint
and exclusive editing; filesystem replacement cannot itself guarantee those facts.
"""

import copy
import ctypes
import hashlib
import json
import os
import tempfile
import tomllib
from pathlib import Path

from .stdio_binding import _relative, _verify_files, digest, load_binding
from .storage import file_lock


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _replace(source, target):
    if os.name == "nt":
        # Preserve original attributes/ACLs; do not ignore merge or ACL failures.
        # https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-replacefilew
        operation = ctypes.WinDLL("kernel32", use_last_error=True).ReplaceFileW
        operation.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        operation.restype = ctypes.c_int
        if not operation(str(target), str(source), None, 0, None, None):
            raise ctypes.WinError(ctypes.get_last_error())
    else:
        os.chmod(source, target.stat().st_mode)
        os.replace(source, target)


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate configuration key")
        value[key] = item
    return value


def _parse(data, suffix):
    text = data.decode("utf-8-sig")
    return tomllib.loads(text) if suffix == ".toml" else json.loads(text, object_pairs_hook=_object)


def _adapter_files(bridge):
    root = Path(bridge).parent
    files = json.loads((root / "checksums.json").read_text(encoding="utf-8"))
    files = {_relative(name): expected for name, expected in files.items()}
    files["checksums.json"] = digest(root / "checksums.json")
    _verify_files(root, files, Path(bridge))
    inventory = json.loads((root / "build-inventory.json").read_text(encoding="utf-8"))
    if inventory.get("adapter_version") != "0.1.0" or inventory.get("engine_included") is not False:
        raise ValueError("Unrecognized standalone adapter package")
    return files


def stage_configuration(config, candidate, binding_path, bridge, server, receipt_dir):
    config, candidate = Path(config).resolve(strict=True), Path(candidate).resolve(strict=True)
    bridge, binding_path = Path(bridge).resolve(strict=True), Path(binding_path).resolve(strict=True)
    if config == candidate or bridge.name.lower() != "origin-stdio-bridge.exe":
        raise ValueError("Separate proposed config and frozen bridge are required")
    bound = load_binding(binding_path)
    bound.verify()
    adapter_files = _adapter_files(bridge)
    before, after = config.read_bytes(), candidate.read_bytes()
    old, new = _parse(before, config.suffix), _parse(after, config.suffix)
    table = "mcp_servers" if config.suffix == ".toml" else "mcpServers"
    entry = old[table][server]
    if [entry.get("command"), *entry.get("args", [])] != bound.command:
        raise ValueError("Original server entry does not exactly match the bound engine")
    proposed = copy.deepcopy(old)
    proposed[table][server]["command"] = str(bridge)
    proposed[table][server]["args"] = ["serve", "--binding", str(binding_path)]
    if new != proposed:
        raise ValueError("Only the selected command and args may change; preserve all other settings")
    destination = Path(receipt_dir)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "before.bin").write_bytes(before)
    (destination / "after.bin").write_bytes(after)
    receipt = {
        "schema_version": 1,
        "config": str(config),
        "server": server,
        "before_sha256": _sha(before),
        "after_sha256": _sha(after),
        "binding": str(binding_path),
        "binding_sha256": digest(binding_path),
        "bridge": str(bridge),
        "bridge_sha256": digest(bridge),
        "adapter_files": adapter_files,
    }
    (destination / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def replace_configuration(receipt_dir, *, rollback=False, checkpoint=False):
    if not checkpoint:
        raise ValueError("Maintenance must confirm host-safe checkpoint and exclusive editing")
    directory = Path(receipt_dir).resolve(strict=True)
    receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
    if receipt.get("schema_version") != 1:
        raise ValueError("Unsupported migration receipt")
    config = Path(receipt["config"])
    if not config.is_absolute() or config.is_symlink():
        raise ValueError("Configuration ownership is unconfirmed")
    before, after = (directory / "before.bin").read_bytes(), (directory / "after.bin").read_bytes()
    if _sha(before) != receipt["before_sha256"] or _sha(after) != receipt["after_sha256"]:
        raise ValueError("Private backup changed")
    expected = receipt["after_sha256" if rollback else "before_sha256"]
    replacement = before if rollback else after
    if not rollback:
        if _adapter_files(receipt["bridge"]) != receipt["adapter_files"]:
            raise ValueError("Staged adapter package changed")
        if (
            digest(receipt["bridge"]) != receipt["bridge_sha256"]
            or digest(receipt["binding"]) != receipt["binding_sha256"]
        ):
            raise ValueError("Staged adapter or binding changed")
        load_binding(receipt["binding"]).verify()
    with file_lock(directory / "migration.lock", timeout=0):
        if digest(config) != expected:
            raise ValueError("Host config changed; refuse to overwrite another edit")
        fd, temporary = tempfile.mkstemp(prefix=".origin-stdio-", dir=config.parent)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(replacement)
                output.flush()
                os.fsync(output.fileno())
            if digest(config) != expected:
                raise ValueError("Host config changed during staging")
            _replace(temporary, config)
            if digest(config) != _sha(replacement):
                raise ValueError("Configuration replacement could not be confirmed")
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
