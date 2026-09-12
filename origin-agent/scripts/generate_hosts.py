"""Generate host-specific packaging from one product identity."""

import json
import shutil
from pathlib import Path

from origin_agent import __version__
from origin_agent.product import DESCRIPTION, WEBSITE

ROOT = Path(__file__).resolve().parents[1]


def write(name, payload):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    receiver = ROOT / "skills/origin-workflow/scripts/receive_artifact.js"
    receiver.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "src/origin_agent/data/receive_artifact.js", receiver)
    identity = {
        "name": "origin-agent",
        "version": __version__,
        "description": "Origin Companion: natural-language workflows, live projects and GUI automation.",
    }
    author = {"name": "Origin Companion contributors"}
    write(
        "plugin.json",
        {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            **identity,
            "license": "MIT",
        },
    )
    write(".claude-plugin/plugin.json", {**identity, "author": author, "license": "MIT"})
    write(
        ".codex-plugin/plugin.json",
        {
            **identity,
            "author": author,
            "license": "MIT",
            "skills": "./skills/",
            "mcpServers": "./.mcp.json",
            "interface": {
                "displayName": "Origin Companion",
                "brandColor": "#183C69",
                "composerIcon": "./assets/icon.svg",
                "logo": "./assets/icon.svg",
                "logoDark": "./assets/icon.svg",
                "shortDescription": DESCRIPTION,
                "longDescription": "Discover installed functions, use Python/LabTalk/Origin C, "
                "or run scientific workflows. Continue editing managed projects and use native GUI controls. "
                "Independent personal project for the specified licensed Origin version.",
                "developerName": author["name"],
                "category": "Productivity",
                "capabilities": ["Read", "Write"],
                "defaultPrompt": [
                    "Inspect my CSV and create an Origin graph.",
                    "Fit my calibration and export an editable project.",
                ],
            },
        },
    )
    overlay = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    write(
        "plugin.json",
        {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            **identity,
            "author": author,
            "license": "MIT",
            "homepage": WEBSITE,
            "extensions": {"com.openai": {"interface": overlay["interface"]}},
        },
    )
    shim = (
        "$p=Join-Path $env:USERPROFILE '.origin-agent\\install.json'; "
        "$i=Get-Content -Raw -Encoding UTF8 -LiteralPath $p|ConvertFrom-Json; & $i.executable serve"
    )
    mcp = {
        "mcpServers": {
            "origin-agent": {
                "type": "stdio",
                "command": "powershell.exe",
                "args": ["-NoProfile", "-NonInteractive", "-Command", shim],
            }
        }
    }
    write(".mcp.json", mcp)
    write("mcp.json", {"$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json", **mcp})
    write(
        "manifest.json",
        {
            "manifest_version": "0.3",
            **identity,
            "display_name": "Origin Companion",
            "icon": "assets/icon.png",
            "author": author,
            "license": "MIT",
            "server": {
                "type": "binary",
                "entry_point": "server/origin-agent.exe",
                "mcp_config": {"command": "${__dirname}/server/origin-agent.exe", "args": ["serve"]},
            },
            "compatibility": {"platforms": ["win32"]},
            "tools_generated": True,
        },
    )
    write("hosts/workbuddy/mcp.json", mcp)
    write(
        "hosts/workbuddy/connector-meta.json",
        {
            "source": "origin-agent",
            "type": "mcp",
            "name": "Origin Companion",
            "name_zh": "Origin Companion · Origin 工作助手",
            "name_en": "Origin Companion",
            "version": __version__,
            "description": identity["description"],
            "description_zh": "用自然语言调用本机正版 Origin，完成导入、作图、拟合、批处理和可编辑工程导出。",
            "description_en": identity["description"],
            "minWorkbuddyVersion": "4.24.0",
            "examples_zh": ["检查 CSV，在 Origin 中绘制两条曲线。", "按实验手册拟合标准曲线并保存 OPJU。"],
            "examples_en": [
                "Inspect this CSV and plot two series.",
                "Fit this calibration and save an OPJU.",
            ],
        },
    )
    shutil.copy2(ROOT / "assets/icon.svg", ROOT / "hosts/workbuddy/icon.svg")


if __name__ == "__main__":
    main()
