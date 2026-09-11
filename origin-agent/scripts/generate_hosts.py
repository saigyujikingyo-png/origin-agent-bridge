"""Generate host-specific packaging from one product identity."""

import json
import shutil
from pathlib import Path

from origin_agent import __version__

ROOT = Path(__file__).resolve().parents[1]


def write(name, payload):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    identity = {
        "name": "origin-agent",
        "version": __version__,
        "description": "Native Origin plots, fits and batches with verified editable OPJU projects.",
    }
    author = {"name": "Origin Agent Bridge contributors"}
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
                "displayName": "Origin Agent Bridge",
                "shortDescription": "Plot and fit with your licensed Origin.",
                "longDescription": "Use native Origin for plots, regression and batches. "
                "Inspect previews and receive editable projects with verification records.",
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
            "display_name": "Origin Agent Bridge",
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
            "name": "Origin Agent Bridge",
            "name_zh": "Origin 科学分析助手",
            "name_en": "Origin Agent Bridge",
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
