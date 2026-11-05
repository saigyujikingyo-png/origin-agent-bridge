"""Build a separate offline candidate; never install or bundle an Origin engine."""

import argparse
import importlib.metadata
import json
import shutil
import subprocess
import sys
import sysconfig
import zipfile
from pathlib import Path

from origin_agent.stdio_binding import digest
from origin_agent.stdio_broker import BRIDGE_VERSION

ROOT = Path(__file__).resolve().parents[1]


def sources():
    paths = list((ROOT / "src/origin_agent").glob("stdio_*.py"))
    paths += [
        ROOT / "src/origin_agent" / name for name in ("__init__.py", "storage.py", "data/stdio_backends.json")
    ]
    paths += [ROOT / "scripts" / name for name in ("build_stdio_bridge.py", "stdio_entry.py")]
    paths += [ROOT / "docs/STDIO_BRIDGE.md", ROOT.parent / "LICENSE"]
    return {p.relative_to(ROOT.parent).as_posix(): digest(p) for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="A new private build directory")
    args = parser.parse_args()
    destination = args.output.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    before = sources()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--onedir",
            "--console",
            "--name",
            "origin-stdio-bridge",
            "--paths",
            str(ROOT / "src"),
            "--distpath",
            str(destination / "dist"),
            "--workpath",
            str(destination / "work"),
            "--specpath",
            str(destination / "work"),
            "--add-data",
            str(ROOT / "src/origin_agent/data/stdio_backends.json") + ";origin_agent/data",
            str(ROOT / "scripts/stdio_entry.py"),
        ],
        check=True,
        cwd=ROOT,
    )
    if before != sources():
        raise RuntimeError("Source changed during freezing; discard this candidate")
    package = destination / "dist/origin-stdio-bridge"
    shutil.copy2(ROOT / "docs/STDIO_BRIDGE.md", package / "README.md")
    shutil.copy2(ROOT.parent / "LICENSE", package / "LICENSE.txt")
    notices = package / "licenses"
    notices.mkdir()
    shutil.copy2(Path(sysconfig.get_path("stdlib")).parent / "LICENSE.txt", notices / "Python.txt")
    distribution = importlib.metadata.distribution("pyinstaller")
    for file in distribution.files:
        if str(file).endswith("licenses/COPYING.txt"):
            shutil.copy2(distribution.locate_file(file), notices / "PyInstaller.txt")
    (notices / "SQLite.txt").write_text(
        "SQLite is in the public domain. https://www.sqlite.org/copyright.html\n", encoding="utf-8"
    )
    inventory = {
        "candidate": True,
        "adapter_version": BRIDGE_VERSION,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_status": subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        ).strip(),
        "source_hashes": before,
        "python_version": sys.version.split()[0],
        "pyinstaller_version": distribution.version,
        "engine_included": False,
        "host_acceptance": "pending",
    }
    (package / "build-inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    hashes = {p.relative_to(package).as_posix(): digest(p) for p in sorted(package.rglob("*")) if p.is_file()}
    (package / "checksums.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    archive = destination / ("origin-stdio-bridge-" + BRIDGE_VERSION + "-candidate-windows-x64.zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(package))
    with zipfile.ZipFile(archive) as output:
        if output.testzip() is not None:
            raise RuntimeError("Candidate ZIP verification failed")
    if before != sources() or digest(package / "README.md") != digest(ROOT / "docs/STDIO_BRIDGE.md"):
        raise RuntimeError("Source or packaged documentation changed during finalization")
    print(json.dumps({"archive": str(archive), "sha256": digest(archive), "files": len(hashes) + 1}))


if __name__ == "__main__":
    main()
