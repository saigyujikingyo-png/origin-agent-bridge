"""Bind an adapter to an unchanged, recognized frozen Origin engine.

Bindings are private local configuration, not publishable receipts. They contain
paths but never environment values. No existing host configuration is edited here.
"""

import hashlib
import json
import os
from pathlib import Path


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def optional_digest(path):
    return digest(path) if Path(path).is_file() else None


def _relative(value):
    if not isinstance(value, str):
        raise ValueError("Invalid package member")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or ":" in value or not value:
        raise ValueError("Invalid package member")
    return value.replace("\\", "/")


def _validate_args(arguments):
    if not isinstance(arguments, list) or not arguments or arguments[0] != "serve":
        raise ValueError("Only the original serve/stdio command is supported")
    allowed = {
        "--transport": {"stdio"},
        "--profile": {"full", "economy"},
        "--vision": {"auto", "off", "on"},
        "--model-preset": {"generic", "deepseek", "gpt-terra", "gemini", "glm", "kimi", "elm"},
    }
    seen = set()
    index = 1
    while index < len(arguments):
        option = arguments[index]
        index += 1
        if "=" in option:
            option, value = option.split("=", 1)
        else:
            if index >= len(arguments):
                raise ValueError("Missing backend argument")
            value = arguments[index]
            index += 1
        if option not in allowed or option in seen or value not in allowed[option]:
            raise ValueError("Unsupported or ambiguous backend argument")
        seen.add(option)


def _verify_files(root, files, executable):
    if not isinstance(files, dict) or not 1 <= len(files) <= 5000:
        raise ValueError("Invalid package inventory")
    for name, expected in files.items():
        relative = _relative(name)
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError("Package member ownership is unconfirmed")
        if not isinstance(expected, str) or len(expected) != 64 or digest(path) != expected:
            raise ValueError("Bound backend content changed")
    executable_relative = executable.relative_to(root).as_posix()
    if executable_relative not in files:
        raise ValueError("Executable is not inventoried")
    server_root = executable.parent
    expected_server = {name for name in files if (root / name).is_relative_to(server_root)}
    actual_server = {path.relative_to(root).as_posix() for path in server_root.rglob("*") if path.is_file()}
    if expected_server != actual_server:
        raise ValueError("Backend runtime file set changed")


def _recognized_inventory(root):
    inventory = json.loads((root / "build-inventory.json").read_text(encoding="utf-8-sig"))
    supported = json.loads(
        (Path(__file__).parent / "data" / "stdio_backends.json").read_text(encoding="utf-8")
    )
    version = inventory.get("version")
    source = supported.get(version)
    if source is None:
        raise ValueError("Backend version has not been reviewed for idle retirement")
    actual_sources = {
        key.replace("\\", "/"): value for key, value in inventory.get("source_hashes", {}).items()
    }
    if any(actual_sources.get(name) not in hashes for name, hashes in source["source_hashes"].items()):
        raise ValueError("Backend source inventory differs from the reviewed release")
    packages = {
        item.get("name", "").lower(): item.get("version")
        for item in inventory.get("packages_in_build_environment", [])
    }
    if packages.get("mcp") != "2.2.0":
        raise ValueError("Backend protocol dependency is not the reviewed version")
    return version, source


def create_binding(executable, arguments, output):
    executable = Path(executable)
    if not executable.is_absolute() or executable.name.lower() != "origin-agent.exe":
        raise ValueError("Use the existing absolute frozen Origin executable, without a shell wrapper")
    executable = executable.resolve(strict=True)
    _validate_args(arguments)
    root = next(
        (parent for parent in list(executable.parents)[:3] if (parent / "build-inventory.json").is_file()),
        None,
    )
    if root is None:
        raise ValueError("A recognized Origin package inventory is required")
    version, source = _recognized_inventory(root)
    files = json.loads((root / "checksums.json").read_text(encoding="utf-8-sig"))
    files = {_relative(key): value for key, value in files.items()}
    files["checksums.json"] = digest(root / "checksums.json")
    _verify_files(root, files, executable)
    value = {
        "schema_version": 1,
        "engine_version": version,
        "source_commit": source["commit"],
        "executable": str(executable),
        "package_root": str(root),
        "arguments": arguments,
        "files": files,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
    return {"engine_version": version, "binding_sha256": digest(output), "package_files": len(files)}


class BackendBinding:
    def __init__(self, path):
        self.path = Path(path).resolve(strict=True)
        self.binding_digest = digest(self.path)
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value.get("schema_version") != 1:
            raise ValueError("Unsupported binding schema")
        self.executable = Path(value["executable"])
        self.package_root = Path(value["package_root"])
        if not self.executable.is_absolute() or not self.package_root.is_absolute():
            raise ValueError("Binding requires absolute package paths")
        if not self.executable.resolve().is_relative_to(self.package_root.resolve()):
            raise ValueError("Backend is outside its bound package")
        _validate_args(value["arguments"])
        self.command = [str(self.executable), *value["arguments"]]
        self.files = value["files"]
        self.version = value["engine_version"]
        version, source = _recognized_inventory(self.package_root)
        if (
            self.executable.name.lower() != "origin-agent.exe"
            or self.version != version
            or value.get("source_commit") != source["commit"]
        ):
            raise ValueError("Binding does not identify a reviewed Origin backend")
        self.cwd = Path.cwd().resolve()
        self.environment = os.environ.copy()
        self.root = Path(
            self.environment.get("ORIGIN_AGENT_HOME", str(Path.home() / ".origin-agent"))
        ).resolve()
        self.profile_digest = optional_digest(self.root / "agent-profile.json")

    def verify(self):
        if digest(self.path) != self.binding_digest:
            raise ValueError("Binding changed during this host connection")
        if Path.cwd().resolve() != self.cwd or os.environ.copy() != self.environment:
            raise ValueError("Host launch context changed")
        if optional_digest(self.root / "agent-profile.json") != self.profile_digest:
            raise ValueError("Origin profile changed; start a new host connection")
        version, _ = _recognized_inventory(self.package_root)
        if version != self.version:
            raise ValueError("Backend version changed")
        inventory_files = json.loads((self.package_root / "checksums.json").read_text(encoding="utf-8-sig"))
        inventory_files = {_relative(key): value for key, value in inventory_files.items()}
        inventory_files["checksums.json"] = digest(self.package_root / "checksums.json")
        if inventory_files != self.files:
            raise ValueError("Binding inventory no longer matches the package")
        _verify_files(self.package_root, self.files, self.executable)


def load_binding(path):
    return BackendBinding(path)
