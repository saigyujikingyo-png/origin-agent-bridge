"""Build an offline Windows bundle, MCPB, host manifests, licences and checksums."""

import argparse
import importlib.metadata
import importlib.util
import json
import shutil
import subprocess
import sys
import sysconfig
import uuid
import zipfile
from pathlib import Path

from origin_agent import __version__
from origin_agent.capabilities import api_index
from origin_agent.storage import sha256

ROOT = Path(__file__).resolve().parents[1]


def frozen_sources():
    sources = [p for p in (ROOT / "src").rglob("*") if p.suffix in (".py", ".json")]
    sources += [
        ROOT / name
        for name in ("pyproject.toml", "uv.lock", "scripts/build_release.py", "scripts/frozen_entry.py")
    ]
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(sources)}


def write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-freeze", action="store_true")
    args = parser.parse_args()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    build_base = Path.home() / ".origin-agent/build"
    run_root = build_base / uuid.uuid4().hex
    run_root.mkdir(parents=True)
    record = ROOT / "build/freeze-location.json"
    source_hashes = frozen_sources()
    if not args.skip_freeze:
        # Freeze the generated Windows UIA interfaces; end users need no writable code cache.
        import os

        from comtypes.client import GetModule

        GetModule(str(Path(os.environ["SystemRoot"]) / "System32/UIAutomationCore.dll"))
        vendor_source = Path(importlib.util.find_spec("originpro").origin).parent
        api_data = run_root / "data/api-index.json"
        write(api_data, api_index(vendor_source))
        shutil.copy2(ROOT / "src/origin_agent/data/coverage.json", api_data.parent / "coverage.json")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--onedir",
                "--console",
                "--name",
                "origin-agent",
                "--paths",
                str(ROOT / "src"),
                "--distpath",
                str(run_root / "frozen"),
                "--workpath",
                str(run_root / "work"),
                "--specpath",
                str(run_root / "work"),
                "--collect-submodules",
                "mcp.server",
                "--collect-submodules",
                "mcp_types",
                "--collect-submodules",
                "originpro",
                "--collect-submodules",
                "OriginExt",
                "--hidden-import",
                "comtypes.gen.UIAutomationClient",
                "--collect-data",
                "jsonschema_specifications",
                "--add-data",
                str(api_data.parent) + ";origin_agent/data",
                "--copy-metadata",
                "originpro",
                "--copy-metadata",
                "OriginExt",
                "--exclude-module",
                "numpy",
                "--exclude-module",
                "pandas",
                "--exclude-module",
                "pytest",
                "--exclude-module",
                "IPython",
                str(ROOT / "scripts/frozen_entry.py"),
            ],
            cwd=ROOT,
            check=True,
        )
        frozen = run_root / "frozen/origin-agent"
        if source_hashes != frozen_sources():
            raise RuntimeError("Source changed during freezing; build again from a stable tree")
        write(record, {"frozen": str(frozen), "source_hashes": source_hashes})
    else:
        cached = json.loads(record.read_text(encoding="utf-8"))
        if cached["source_hashes"] != source_hashes:
            raise RuntimeError("Source changed; run a full freeze before packaging")
        frozen = Path(cached["frozen"])
    bundle = run_root / f"origin-agent-{__version__}-windows-x64"
    bundle.mkdir()
    shutil.copytree(frozen, bundle / "server")
    for directory in ("skills", "assets", "docs", "examples", ".codex-plugin", ".claude-plugin"):
        if (ROOT / directory).exists():
            shutil.copytree(ROOT / directory, bundle / directory)
    for filename in ("LICENSE", "README.md", "plugin.json", "mcp.json", ".mcp.json", "manifest.json"):
        shutil.copy2(ROOT / filename, bundle / filename)
    for filename in ("Install.ps1", "Install.cmd", "Connect-ChatGPT.ps1"):
        shutil.copy2(ROOT / "scripts" / filename, bundle / filename)
    shutil.copytree(ROOT / "hosts/workbuddy", bundle / "workbuddy")
    notices = bundle / "third-party-licenses"
    notices.mkdir()
    packages = []
    excluded = {"pytest", "ruff", "iniconfig", "pluggy", "pygments", "origin-agent-bridge"}
    for dependency in sorted(importlib.metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        name, version = dependency.metadata["Name"], dependency.version
        if name.lower() in excluded:
            continue
        files = []
        for file in dependency.files or []:
            if file.name.lower().startswith(("license", "copying", "notice")):
                source = Path(dependency.locate_file(file))
                if source.is_file():
                    target = notices / name / str(file).replace("/", "_").replace("\\", "_")
                    target.parent.mkdir(exist_ok=True)
                    shutil.copy2(source, target)
                    files.append(str(target.relative_to(bundle)).replace("\\", "/"))
        packages.append({"name": name, "version": version, "license_files": files})
    python_license = Path(sysconfig.get_config_var("installed_base")) / "LICENSE.txt"
    if python_license.exists():
        shutil.copy2(python_license, notices / "Python-LICENSE.txt")
    write(
        bundle / "build-inventory.json",
        {
            "version": __version__,
            "python": sys.version,
            "packages_in_build_environment": packages,
            "origin_application_included": False,
            "source_hashes": source_hashes,
        },
    )
    checksums = {
        str(p.relative_to(bundle)).replace("\\", "/"): sha256(p)
        for p in sorted(bundle.rglob("*"))
        if p.is_file()
    }
    write(bundle / "checksums.json", checksums)
    zip_path = dist / (bundle.name + ".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(bundle))
    # MCPB is a ZIP with manifest.json at its root; validate with the official mcpb CLI separately.
    mcpb = dist / f"origin-agent-{__version__}-windows-x64.mcpb"
    shutil.copy2(zip_path, mcpb)
    hashes = {p.name: sha256(p) for p in (zip_path, mcpb)}
    write(dist / "SHA256SUMS.json", hashes)
    print(
        json.dumps(
            {
                "bundle": str(bundle),
                "archive": str(zip_path),
                "mcpb": str(mcpb),
                "zip_mib": round(zip_path.stat().st_size / 1024**2, 2),
                "sha256": hashes,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
