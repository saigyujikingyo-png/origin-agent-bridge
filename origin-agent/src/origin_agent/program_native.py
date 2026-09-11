"""Execute trusted general programs in an owned Origin instance, with observable outputs."""

import contextlib
import mimetypes
import shutil
import time

from . import __version__
from .origin_runtime import connect_origin
from .programs import OriginProgram, check_readback, load_program
from .storage import Store, json_bytes, sha256, write_json


def snapshot(op):
    pages = []
    for page in op.pages():
        item = {"name": page.name, "long_name": page.lname, "type": type(page).__name__}
        if item["type"] == "WBook":
            item["sheets"] = [
                {"name": sheet.name, "rows": sheet.rows, "columns": sheet.cols} for sheet in page
            ]
        elif item["type"] == "MBook":
            # MSheet exposes shape/depth, not WSheet.rows/cols; do not import NumPy.
            item["sheets"] = [
                {
                    "name": sheet.name,
                    "rows": sheet.shape[0],
                    "columns": sheet.shape[1],
                    "matrices": sheet.depth,
                }
                for sheet in page
            ]
        pages.append(item)
    return {"pages": pages, "graphs": [p["name"] for p in pages if p["type"] == "GPage"]}


def _decode_log(path):
    if not path.exists():
        return ""
    raw = path.read_bytes()[: 128 * 1024]
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def run_program(store: Store, identifier: str, plan_id: str, *, active: dict | None = None):
    owned = active is None
    op = None
    plan = load_program(store, plan_id)
    program = OriginProgram.model_validate(plan["workflow"])
    directory = store.path("jobs", identifier)
    plan_dir = store.path("plans", plan_id)
    started = time.monotonic()
    progress = {"stage": "starting_origin", "kind": "program"}

    def checkpoint(stage):
        progress.update(stage=stage, elapsed_seconds=round(time.monotonic() - started, 2))
        write_json(directory / "progress.json", progress)
        if (directory / "cancel.json").exists():
            raise RuntimeError("Cancelled")

    extension = {"python": "py", "labtalk": "ogs", "origin_c": "c"}[program.language]
    source_file = directory / f"program.{extension}"
    source_file.write_text(program.code, encoding="utf-8")
    outputs = [source_file]
    try:
        checkpoint("starting_origin")
        runtime = connect_origin() if owned else active
        op, engine = runtime["op"], runtime["engine"]
        progress.update(origin_pid=runtime["origin_pid"], origin_created=runtime["origin_created"])
        checkpoint("connected")
        write_json(store.root / "last-native-engine.json", engine)
        if owned:
            op.new()
        inputs = {}
        # Execute against copies so changing a source worksheet never overwrites the input snapshot.
        input_dir = directory / "inputs"
        input_dir.mkdir(exist_ok=True)
        for alias, source in plan["sources"].items():
            target = input_dir / source["file"]
            shutil.copyfile(plan_dir / source["file"], target)
            if sha256(target) != source["sha256"]:
                raise ValueError("Program input changed while creating its execution copy")
            inputs[alias] = target
        if "__project__" in inputs:
            if not owned:
                raise ValueError("A session program cannot replace the active project")
            if not op.open(str(inputs["__project__"])):
                raise RuntimeError("Origin could not open the copied project")
        before_state = snapshot(op)
        checkpoint("executing_program")
        log = directory / "labtalk.log"
        op.set_lt_str("oa_log", log.as_posix())
        op.set_lt_str("oa_output", directory.as_posix())
        for alias, path in inputs.items():
            op.set_lt_str("oa_input_" + alias, path.as_posix())
        if not op.lt_exec('type -gbef "%(oa_log$)";'):
            raise RuntimeError("Could not start Origin script logging")
        results = {}
        try:
            if program.language == "python":
                namespace = {
                    "op": op,
                    "INPUTS": inputs,
                    "OUTPUT_DIR": directory,
                    "RESULTS": results,
                    "__name__": "__origin_program__",
                    "__file__": str(source_file),
                }
                exec(compile(program.code, str(source_file), "exec"), namespace)
                results = namespace["RESULTS"]
            else:
                if program.language == "origin_c":
                    # The Origin C compiler requires Windows separators (forward slashes return 3).
                    op.set_lt_str("oa_source", str(source_file))
                    rc = op.lt_float('run.LoadOC("%(oa_source$)")')
                    if rc != 0:
                        raise RuntimeError(f"Origin C compilation failed (code {rc})")
                code = program.entrypoint if program.language == "origin_c" else program.code
                if not op.lt_exec(code):
                    raise RuntimeError("Origin reported a LabTalk execution failure")
            for name, check in program.readbacks.items():
                value = (
                    op.lt_float(check.expression)
                    if check.type == "number"
                    else op.get_lt_str(check.expression)
                )
                results[name] = check_readback(value, check)
        finally:
            op.lt_exec("type -ge;")
        if not isinstance(results, dict) or len(json_bytes(results)) > 128 * 1024:
            raise ValueError("RESULTS must be a finite JSON object <=128 KiB; put large data in output_files")
        checkpoint("exporting")
        after_state = snapshot(op)
        for index, name in enumerate(after_state["graphs"], 1):
            graph = op.find_graph(name)
            for fmt in dict.fromkeys(program.graph_formats):
                target = directory / f"graph-{index:03d}.{fmt}"
                if not graph.save_fig(str(target), type=fmt, width=1600):
                    raise RuntimeError(f"Origin graph export failed: {name}")
                outputs.append(target)
        for name in program.output_files:
            target = directory / name
            if target.resolve().parent != directory.resolve() or target.is_symlink():
                raise ValueError("Output must be a regular file directly in this job directory")
            outputs.append(target)
        project = directory / "project.opju"
        if not op.save(str(project)):
            raise RuntimeError("Origin could not save the program project")
        outputs.append(project)
        if owned:
            checkpoint("reopening_project")
            op.new()
            if not op.open(str(project)):
                raise RuntimeError("Saved project could not be reopened")
        reopened = snapshot(op)
        if reopened != after_state:
            raise RuntimeError("Saved project structure differs after reopening")
        pngs = 0
        for path in outputs:
            if not path.is_file() or not 0 < path.stat().st_size <= 256 * 1024 * 1024:
                raise RuntimeError(f"Missing, empty or oversized output: {path.name}")
            if path.suffix.lower() == ".png":
                from PIL import Image

                with Image.open(path) as img:
                    img.verify()
                pngs += 1
            elif path.suffix.lower() == ".pdf":
                with path.open("rb") as stream:
                    if stream.read(5) != b"%PDF-":
                        raise RuntimeError("Invalid PDF output")
            elif path.suffix.lower() == ".svg":
                with path.open(encoding="utf-8-sig") as stream:
                    if "<svg" not in stream.read(4096):
                        raise RuntimeError("Invalid SVG output")
        result_file = directory / "result.json"
        write_json(
            result_file,
            {
                "results": results,
                "labtalk_output": _decode_log(log),
                "before": before_state,
                "after": reopened,
            },
        )
        state_file = directory / "state.json"
        write_json(state_file, reopened)
        outputs += [result_file, state_file]
        verification = {
            "vendor_native": True,
            "project_reopened": owned,
            "structure_roundtrip": owned,
            "live_session_preserved": not owned,
            "numeric_data_roundtrip": False,
            "independent_scientific_validation": False,
            "explicit_postconditions_passed": sum(c.expected is not None for c in program.readbacks.values()),
            "pngs_decoded": pngs,
            "visual_review": "Agent must inspect exported figures",
            "seconds": round(time.monotonic() - started, 3),
        }
        write_json(
            directory / "manifest.json",
            {
                "plugin_version": __version__,
                "kind": "program",
                "job_id": identifier,
                "plan_id": plan_id,
                "engine": engine,
                "workflow": program.model_dump(),
                "sources": plan["sources"],
                "summary": [
                    {
                        "title": program.title,
                        "language": program.language,
                        "results_artifact": f"{identifier}/result.json",
                        "graphs": len(reopened["graphs"]),
                    }
                ],
                "project_index": reopened,
                "verification": verification,
                "execution_permissions": "Unsandboxed trusted code under the current Windows user",
                "artifacts": [
                    {
                        "name": p.name,
                        "bytes": p.stat().st_size,
                        "sha256": sha256(p),
                        "mime_type": mimetypes.guess_type(p.name)[0] or "application/octet-stream",
                    }
                    for p in outputs
                ],
            },
        )
        checkpoint("finished")
    except Exception as exc:
        write_json(
            directory / "error.json",
            {
                "type": type(exc).__name__,
                "message": str(exc)[:1500],
                "labtalk_output": _decode_log(directory / "labtalk.log")[-12000:],
            },
        )
        raise
    finally:
        if owned and op is not None:
            with contextlib.suppress(Exception):
                op.exit()
