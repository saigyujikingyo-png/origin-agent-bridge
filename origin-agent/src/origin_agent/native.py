"""Only this short-lived worker imports originpro. All operations are fixed and audited."""

import csv
import hashlib
import math
import mimetypes
import time
from pathlib import Path

import psutil

from . import __version__
from .datasets import column_digest, dataset_table, numeric_columns
from .graph_text import origin_text
from .models import Workflow
from .planning import load_plan
from .storage import Store, read_json, sha256, write_json
from .target import require_target

COLORS = [(0, 114, 178), (213, 94, 0), (0, 158, 115), (204, 121, 167), (230, 159, 0)]


def reference_fit(x: list[float], y: list[float], intercept: str):
    """Independent coefficient/RSS oracle, never a substitute for native Origin fitting."""
    if intercept == "zero":
        slope = math.fsum(a * b for a, b in zip(x, y, strict=True)) / math.fsum(a * a for a in x)
        offset = 0.0
    else:
        mx, my = math.fsum(x) / len(x), math.fsum(y) / len(y)
        slope = math.fsum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / math.fsum(
            (a - mx) ** 2 for a in x
        )
        offset = my - slope * mx
    residuals = [b - (offset + slope * a) for a, b in zip(x, y, strict=True)]
    return slope, offset, math.fsum(r * r for r in residuals)


def origin_processes():
    processes = {}
    for process in psutil.process_iter(["pid", "name", "create_time", "exe"]):
        if (process.info["name"] or "").lower() == "origin64.exe":
            processes[process.pid] = process.info
    return processes


def _fit(op, sheet, x_index, y_index, analysis):
    fit = op.LinearFit()
    fit.set_data(sheet, x_index, y_index)
    # Origin auto-detects adjacent Y-error columns. Force the plan's unweighted model.
    # Fit.ErrBarWeight=0 is ERRBARWEIGHT_NO_WEIGHTING in Origin's stats_types.h.
    fit._set("Fit.ErrBarWeight", 0)
    if analysis.intercept == "zero":
        fit.fix_intercept(0.0)
    result = fit.result()
    # The vendor's documented result/report lifecycle runs two short native fits.
    report_fit = op.LinearFit()
    report_fit.set_data(sheet, x_index, y_index)
    report_fit._set("Fit.ErrBarWeight", 0)
    if analysis.intercept == "zero":
        report_fit.fix_intercept(0.0)
    report, curve = report_fit.report()
    weight_modes = [
        op.lt_float(f"{item._get_tree_name()}.GUI.Fit.ErrBarWeight") for item in (fit, report_fit)
    ]
    del fit, report_fit
    if not report or not curve or not op.find_sheet("w", report) or not op.find_sheet("w", curve):
        raise RuntimeError("Origin did not produce a native fit report and curve")
    if weight_modes != [0.0, 0.0]:
        raise RuntimeError("Origin fitting weights differ from the explicit plan")
    return result, report, curve


def _draw_title(layer, text: str, preset: str):
    """Create real graph text through COM; a graph long name is not an exported title."""
    title = layer.add_label(origin_text(text))
    if title is None:
        raise RuntimeError("Origin could not create the graph title")
    title.set_int("attach", 0)
    title.set_int("clip", 0)
    title.set_int("link", 0)
    title.set_float("fsize", 24 if preset == "presentation" else 20)
    title.set_int("wrap", 1)
    title.set_float("box", 95)
    left, right, *_ = layer.xlim
    bottom, top, *_ = layer.ylim
    # Reserve page space from Origin's measured wrapped text height. Keep the
    # bottom axis fixed, so long/Unicode titles remain inside exported pages.
    layer.set_int("unit", 1)
    frame_top, frame_height = layer.get_float("top"), layer.get_float("height")
    title_height = title.get_float("dy") / (top - bottom) * frame_height
    required_top = title_height + 4.5
    if required_top > frame_top:
        layer.set_float("top", required_top)
        layer.set_float("height", frame_height - (required_top - frame_top))
    title.set_float("x", (left + right) / 2)
    title.set_float("y", top + title.get_float("dy") / 2 + (top - bottom) * 0.025)
    return title.name


def run_native(store: Store, identifier: str, plan_id: str):
    import originpro as op

    directory = store.path("jobs", identifier)
    plan = load_plan(store, plan_id)
    workflow = Workflow.model_validate(plan["workflow"])
    started = time.monotonic()
    progress = {"stage": "starting_origin", "completed_panels": 0, "total_panels": len(workflow.panels)}

    def checkpoint(stage):
        progress["stage"] = stage
        progress["elapsed_seconds"] = round(time.monotonic() - started, 2)
        write_json(directory / "progress.json", progress)
        if (directory / "cancel.json").exists():
            raise RuntimeError("Cancelled")

    outputs = []
    summaries, references, data_refs, graph_refs = [], [], [], []
    graph_text_refs = []
    tables = {}
    try:
        checkpoint("starting_origin")
        before = origin_processes()
        op.set_show(False)  # originpro Application() creates an isolated instance; never call attach().
        after = origin_processes()
        engine = {
            "version": op.lt_float("@V"),
            "bitness": op.lt_int("@VB"),
            "edition": "OriginPro" if op.lt_int("@IM") == 2 else "Origin",
            "demo": op.lt_int("@VM"),
            "executable_directory": op.path("e"),
            "originpro": "1.1.15",
            "OriginExt": "1.2.5",
        }
        unique = [
            p
            for pid, p in after.items()
            if pid not in before
            and p["exe"]
            and Path(p["exe"]).parent.resolve() == Path(op.path("e")).resolve()
        ]
        if len(unique) == 1:
            progress["origin_pid"] = unique[0]["pid"]
            progress["origin_created"] = unique[0]["create_time"]
        checkpoint("connected")
        import os

        explicit = os.environ.get("ORIGIN_AGENT_EXECUTABLE")
        if explicit and Path(explicit).resolve().parent != Path(op.path("e")).resolve():
            raise RuntimeError(
                "COM activated a different Origin installation; fix COM registration for this user"
            )
        require_target(engine)
        write_json(store.root / "last-native-engine.json", engine)
        op.new()
        for panel_index, panel in enumerate(workflow.panels, 1):
            checkpoint(f"panel_{panel_index}_import")
            if panel.dataset_id not in tables:
                tables[panel.dataset_id] = dataset_table(store, panel.dataset_id)
            meta, headers, rows = tables[panel.dataset_id]
            if meta["sha256"] != plan["sources"][panel.dataset_id]["sha256"]:
                raise RuntimeError("Input changed since planning")
            names = list(dict.fromkeys([panel.x, *panel.y, *panel.y_errors.values()]))
            numeric = numeric_columns(headers, rows, names)
            book = op.new_book("w", lname=panel.title)
            sheet = book[0]
            sheet.cols = len(names)
            for column_index, name in enumerate(names):
                axis = "X" if column_index == 0 else "Y"
                if name in panel.y_errors.values():
                    axis = "E"
                sheet.from_list(column_index, numeric[name], lname=name, axis=axis)
            data_refs.append(
                {
                    "sheet": sheet.lt_range(),
                    "columns": len(names),
                    "rows": len(rows),
                    "sha256": column_digest([numeric[n] for n in names]),
                }
            )
            curves = {}
            for series_index, name in enumerate(panel.y, 1):
                yi = names.index(name)
                if panel.analysis:
                    checkpoint(f"panel_{panel_index}_fit_{series_index}")
                    result, report, curve = _fit(op, sheet, 0, yi, panel.analysis)
                    references.append({"report": report, "curve": curve})
                    parameters, stats = result["Parameters"], result["RegStats"]["C1"]
                    slope, intercept = (
                        float(parameters["Slope"]["Value"]),
                        float(parameters["Intercept"]["Value"]),
                    )
                    x, y = numeric[panel.x], numeric[name]
                    expected = reference_fit(x, y, panel.analysis.intercept)
                    if not all(
                        math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-10)
                        for a, b in zip((slope, intercept, float(stats["SSR"])), expected, strict=True)
                    ):
                        raise RuntimeError(
                            "Native fit disagrees with independent coefficient/RSS verification"
                        )
                    if int(stats["N"]) != len(rows):
                        raise RuntimeError(
                            "Native fit row count differs from source; no silent row omission allowed"
                        )
                    curves[name] = curve
                    summary = {
                        "panel": panel_index,
                        "series": name,
                        "n": len(rows),
                        "slope": slope,
                        "intercept": intercept,
                        "slope_se": float(parameters["Slope"]["Error"]),
                        "r_squared_origin": float(stats["RSqCOD"]),
                        "residual_sum_squares": float(stats["SSR"]),
                        "intercept_mode": panel.analysis.intercept,
                        "weighting": "none",
                        "coefficient_rss_crosscheck": True,
                    }
                    if panel.analysis.kind == "beer_lambert":
                        analysis = panel.analysis
                        if slope <= 0:
                            raise RuntimeError(
                                "Beer-Lambert calibration slope must be positive; inspect inputs/model"
                            )
                        if analysis.unknown_absorbance is not None:
                            concentration = (analysis.unknown_absorbance - intercept) / slope
                            summary["unknown_concentration_in_x_units"] = concentration
                            summary["extrapolation"] = not min(x) <= concentration <= max(x)
                            summary["unknown_uncertainty"] = (
                                "not calculated: measurement uncertainty not provided"
                            )
                        if analysis.path_length_cm is not None:
                            summary["molar_absorptivity_L_mol_cm"] = slope / (
                                analysis.path_length_cm * analysis.concentration_scale_molar
                            )
                    stem = f"panel-{panel_index:02d}-fit-{series_index:02d}"
                    # Omit vendor report user name/time from the machine-readable summary.
                    fit_path = directory / f"{stem}.json"
                    write_json(
                        fit_path,
                        {
                            "summary": summary,
                            "parameters": parameters,
                            "statistics": stats,
                            "native_report": report,
                            "native_curve": curve,
                        },
                    )
                    residual_path = directory / f"{stem}-residuals.csv"
                    with residual_path.open("w", encoding="utf-8", newline="") as stream:
                        writer = csv.writer(stream)
                        writer.writerow(["x", "observed_y", "fitted_y", "residual"])
                        writer.writerows(
                            [a, b, intercept + slope * a, b - (intercept + slope * a)]
                            for a, b in zip(x, y, strict=True)
                        )
                    outputs.extend([fit_path, residual_path])
                    summaries.append(summary)
            graph = op.new_graph(template="Origin", lname=panel.title)
            graph_refs.append(graph.name)
            layer = graph[0]
            # Direct COM text assignment avoids interpolating user strings into LabTalk.
            layer.label("xb").text = origin_text(panel.style.x_label or panel.x)
            layer.label("yl").text = origin_text(
                panel.style.y_label or (panel.y[0] if len(panel.y) == 1 else "Value")
            )
            for label_name in ("xb", "yl"):
                layer.label(label_name).set_float("fsize", 18 if panel.style.preset == "presentation" else 14)
            plot_type = {"scatter": "s", "line": "l", "line_symbol": "y"}[panel.style.plot]
            for index, name in enumerate(panel.y):
                error_column = names.index(panel.y_errors[name]) if name in panel.y_errors else -1
                plot = layer.add_plot(
                    sheet, colx=0, coly=names.index(name), type=plot_type, colyerr=error_column
                )
                color = (
                    panel.style.colors[index % len(panel.style.colors)]
                    if panel.style.colors
                    else COLORS[index % len(COLORS)]
                )
                plot.color = color
                plot.symbol_size = 6 if panel.style.preset == "report" else 9
                plot.symbol_kind = [1, 2, 3, 4, 5][index % 5]
                if name in curves:
                    fit_plot = layer.add_plot(op.find_sheet("w", curves[name]), colx=0, coly=1, type="l")
                    fit_plot.color = color
            layer.rescale()
            # Reserve room for the legend so it does not cover the highest points.
            low, high, *_ = layer.ylim
            layer.ylim = (low, high + (high - low) * min(0.6, 0.2 + 0.035 * len(panel.y)))
            title_name = _draw_title(layer, panel.title, panel.style.preset)
            graph_text_refs.append(
                {
                    "graph": graph.name,
                    "labels": {
                        title_name: origin_text(panel.title),
                        "xb": layer.label("xb").text,
                        "yl": layer.label("yl").text,
                    },
                }
            )
            for extension in workflow.formats:
                target = directory / f"panel-{panel_index:02d}.{extension}"
                exported = graph.save_fig(str(target), type=extension, width=panel.style.width)
                if not exported or not target.is_file():
                    raise RuntimeError(f"Origin {extension} export failed")
                outputs.append(target)
            progress["completed_panels"] = panel_index
        checkpoint("saving_project")
        project = directory / "project.opju"
        if not op.save(str(project)):
            raise RuntimeError("Origin project save failed")
        outputs.append(project)
        checkpoint("reopening_and_verifying")
        op.new()
        # Reopen only our own generated project in the isolated instance.
        # Origin 2026b's readonly loader does not provide a reliable data roundtrip through COM.
        if not op.open(str(project)):
            raise RuntimeError("Origin could not reopen its saved project")
        for ref in data_refs:
            sheet = op.find_sheet("w", ref["sheet"])
            if not sheet:
                raise RuntimeError("Saved project is missing its source worksheet")
            columns = [sheet.to_list(index) for index in range(ref["columns"])]
            if column_digest(columns) != ref["sha256"]:
                raise RuntimeError("Saved project data do not match the input snapshot")
        for name in graph_refs:
            if not op.find_graph(name):
                raise RuntimeError("Saved project is missing a graph")
        for ref in graph_text_refs:
            layer = op.find_graph(ref["graph"])[0]
            for label_name, expected_text in ref["labels"].items():
                label = layer.label(label_name)
                if label is None or label.text != expected_text:
                    raise RuntimeError("Saved project graph text differs from the requested title/axes")
        for ref in references:
            if not op.find_sheet("w", ref["report"]) or not op.find_sheet("w", ref["curve"]):
                raise RuntimeError("Saved project is missing a native fit report/curve")
        from PIL import Image

        for path in outputs:
            if path.stat().st_size == 0 or path.stat().st_size > 256 * 1024 * 1024:
                raise RuntimeError("Output file has an invalid size")
            if path.suffix == ".png":
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    if image.width < 600 or image.height < 300:
                        raise RuntimeError("Graph export has unexpected dimensions")
            if path.suffix == ".pdf" and not path.read_bytes().startswith(b"%PDF-"):
                raise RuntimeError("PDF signature check failed")
            if path.suffix == ".svg" and "<svg" not in path.read_text(encoding="utf-8-sig")[:4096]:
                raise RuntimeError("SVG document check failed")
        checkpoint("verified")
        verification = {
            "vendor_native": True,
            "project_reopened": True,
            "data_roundtrip": True,
            "graphs_reopened": len(graph_refs),
            "graph_text_roundtrip": True,
            "titles_reopened": len(graph_text_refs),
            "native_reports_reopened": len(references),
            "png_decoded": True,
            "visual_review": "preview should be reviewed by the agent/user",
            "seconds": round(time.monotonic() - started, 3),
        }
        artifact_rows = [
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            }
            for path in outputs
        ]
        manifest = {
            "plugin_version": __version__,
            "job_id": identifier,
            "plan_id": plan_id,
            "engine": engine,
            "workflow": workflow.model_dump(),
            "sources": plan["sources"],
            "summary": summaries or [{"panels": len(graph_refs), "analysis": "plot only"}],
            "verification": verification,
            "project_index": {
                "data": data_refs,
                "graphs": graph_refs,
                "fits": references,
                "graph_text": graph_text_refs,
            },
            "artifacts": artifact_rows,
        }
        write_json(directory / "manifest.json", manifest)
    except Exception as exc:
        write_json(directory / "error.json", {"type": type(exc).__name__, "message": str(exc)[:1500]})
        raise
    finally:
        op.exit()


def artifact_path(store: Store, artifact_id: str):
    identifier, name = artifact_id.split("/", 1)
    directory = store.path("jobs", identifier)
    if Path(name).name != name or "/" in name or "\\" in name:
        raise ValueError("Invalid artifact name")
    from .jobs import get_job

    if get_job(store, identifier, kick=False)["state"] != "succeeded":
        raise ValueError("Artifacts are available only after successful native verification")
    path = directory / name
    manifest_path = directory / "manifest.json"
    if any(p.is_symlink() or p.is_junction() for p in (directory, path, manifest_path)):
        raise ValueError("Artifact links are not permitted")
    manifest = read_json(manifest_path)
    if name == "manifest.json":
        return directory / name, "application/json"
    entry = next((entry for entry in manifest["artifacts"] if entry["name"] == name), None)
    if entry is None:
        raise ValueError("Unknown artifact")
    path = directory / name
    if sha256(path) != entry["sha256"]:
        raise ValueError("Artifact has changed since verification")
    return path, entry["mime_type"]


def artifact_bytes(store: Store, artifact_id: str):
    """Read bounded bytes and compare the payload against the completed manifest."""
    path, mime = artifact_path(store, artifact_id)
    manifest = read_json(path.parent / "manifest.json")
    expected = (
        None
        if path.name == "manifest.json"
        else next(entry["sha256"] for entry in manifest["artifacts"] if entry["name"] == path.name)
    )
    limit = 32 * 1024 * 1024
    if path.stat().st_size > limit:
        raise ValueError("MCP binary transfer limit is 32 MiB; use the local artifact path")
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("MCP binary transfer limit is 32 MiB; use the local artifact path")
    if expected is not None and hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("Artifact changed during transfer; refusing unverified bytes")
    return path, mime, payload
