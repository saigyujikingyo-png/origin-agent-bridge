"""One discovery implementation shared by status, planning and native verification."""

import importlib.metadata
import os
import platform
from pathlib import Path


def discover() -> dict:
    candidates = []
    explicit = os.environ.get("ORIGIN_AGENT_EXECUTABLE")
    if explicit:
        candidates.append(Path(explicit))
    if os.name == "nt":
        import winreg

        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive, r"Software\OriginLab", access=winreg.KEY_READ | view) as parent:
                        for index in range(winreg.QueryInfoKey(parent)[0]):
                            name = winreg.EnumKey(parent, index)
                            try:
                                with winreg.OpenKey(parent, name + r"\International") as key:
                                    directory = winreg.QueryValueEx(key, "Executable Path")[0]
                                    candidates.append(Path(directory) / "Origin64.exe")
                            except OSError:
                                pass
                except OSError:
                    pass
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            base = Path(os.environ.get(variable, "C:/Program Files")) / "OriginLab"
            if base.is_dir():
                candidates.extend(sorted(base.glob("Origin*/Origin64.exe"), reverse=True))
    available = list(dict.fromkeys(str(p.resolve()) for p in candidates if p.is_file()))
    dependencies = {}
    for name in ("originpro", "OriginExt"):
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = None
    return {
        "platform": platform.system(),
        "architecture": platform.machine(),
        "installations": available,
        "configured_executable": explicit,
        "dependencies": dependencies,
        "native_ready_to_probe": bool(available) and all(dependencies.values()),
        "connection_policy": "new isolated Application; verify actual executable directory at runtime",
    }
