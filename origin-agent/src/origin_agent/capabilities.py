"""On-demand discovery, not a giant list of model tools or a hardcoded function ceiling."""

import ast
import importlib.util
import json
import time
from collections import Counter
from functools import lru_cache
from pathlib import Path

from .discovery import discover

REFERENCES = {
    "programming": "https://docs.originlab.com/origin-help/programming-intro/",
    "python": "https://docs.originlab.com/originpro/annotated.html",
    "labtalk": "https://docs.originlab.com/labtalk/guide/",
    "xfunctions": "https://docs.originlab.com/x-function/ref/",
    "origin_c": "https://docs.originlab.com/originc/",
    "com": "https://docs.originlab.com/com/",
    "script_output": "https://docs.originlab.com/labtalk/guide/debugging-tools/",
}


def api_index(package: Path) -> list[dict]:
    rows = []
    for path in sorted(package.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in tree.body:
            if not isinstance(node, (ast.ClassDef, ast.FunctionDef)) or node.name.startswith("_"):
                continue
            members = [node]
            if isinstance(node, ast.ClassDef):
                members += [
                    m for m in node.body if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")
                ]
            for member in members:
                name = node.name if member is node else f"{node.name}.{member.name}"
                signature = ast.unparse(member.args) if isinstance(member, ast.FunctionDef) else ""
                rows.append(
                    {
                        "id": f"api:{path.stem}.{name}",
                        "kind": "api",
                        "name": name,
                        "category": path.stem,
                        "signature": signature,
                        "help": (ast.get_docstring(member) or "")[:10000],
                        "reference": REFERENCES["python"],
                    }
                )
    return rows


@lru_cache(maxsize=2)
def _index(installation: str, time_bucket: int):
    rows = [
        {
            "id": f"documentation:{name}",
            "kind": "documentation",
            "name": name,
            "reference": url,
            "category": "official",
        }
        for name, url in REFERENCES.items()
    ]
    if installation:
        base = Path(installation).parent
        for folder, pattern, kind in (
            ("X-Functions", "*.OXF", "xfunction"),
            ("FitFunc", "*.FDF", "fitting"),
            ("Templates", "*", "template"),
            ("", "*.ot*", "template"),
        ):
            root = base / folder
            paths = root.rglob(pattern) if folder else root.glob(pattern)
            for path in sorted(paths):
                if not path.is_file() or (
                    kind == "template"
                    and path.suffix.lower() not in (".otp", ".otpu", ".otw", ".otwu", ".otm", ".otmu")
                ):
                    continue
                relative = path.relative_to(root).as_posix()
                entry = {
                    "id": f"{kind}:{relative}",
                    "kind": kind,
                    "name": path.stem,
                    "category": path.parent.relative_to(root).as_posix(),
                    "local_path": str(path),
                }
                if kind == "xfunction":
                    entry["help_command"] = f"{path.stem} -h;"
                    entry["reference"] = REFERENCES["xfunctions"]
                elif kind == "fitting":
                    entry["usage"] = f"op.NLFit({path.stem!r})"
                rows.append(entry)
    bundled = Path(__file__).with_name("data") / "api-index.json"
    if bundled.exists():
        rows += json.loads(bundled.read_text(encoding="utf-8"))
    else:
        spec = importlib.util.find_spec("originpro")
        if spec and spec.origin:
            rows += api_index(Path(spec.origin).parent)
    return rows


def capabilities(
    query: str = "", kind: str = "all", limit: int = 12, offset: int = 0, detail_id: str | None = None
) -> dict:
    if not 1 <= limit <= 30 or offset < 0 or len(query) > 200:
        raise ValueError("Use limit 1..30, offset >=0 and query <=200 characters")
    state = discover()
    installation = state["installations"][0] if state["installations"] else ""
    rows = _index(installation, int(time.monotonic() // 300))
    contract = {
        "installation": installation,
        "counts": dict(Counter(r["kind"] for r in rows)),
        "availability": "Installed/documented, not a claim of licensing or successful execution",
        "execution": "origin_run_program supports Python/originpro/COM, LabTalk/X-Functions, Origin C",
        "gui_only": "Not yet covered by a persistent interactive GUI adapter",
    }
    if detail_id:
        row = next((r for r in rows if r["id"] == detail_id), None)
        if row is None:
            raise ValueError("Unknown capability ID; search again on this computer")
        return {**contract, "entry": row}
    terms = query.casefold().split()
    selected = [
        r
        for r in rows
        if (kind == "all" or r["kind"] == kind)
        and all(
            term in (r["name"] + " " + r["category"] + " " + r.get("help", "")).casefold() for term in terms
        )
    ]
    selected.sort(key=lambda r: (r["name"].casefold() != query.casefold(), r["kind"], r["name"]))
    return {
        **contract,
        "total_matches": len(selected),
        "offset": offset,
        "next_offset": offset + limit if offset + limit < len(selected) else None,
        "entries": [
            {k: v for k, v in r.items() if k not in ("help", "local_path")}
            for r in selected[offset : offset + limit]
        ],
    }
