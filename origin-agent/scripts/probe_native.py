"""Development-only isolated native probe. Never attaches to an existing project."""

import json
import sys
import time
from pathlib import Path

import originpro as op

out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
started = time.monotonic()
try:
    op.set_show(False)
    print(
        json.dumps(
            {
                "version": op.lt_float("@V"),
                "bitness": op.lt_int("@VB"),
                "edition": op.lt_int("@IM"),
                "demo": op.lt_int("@VM"),
                "application_path": op.path("e"),
            }
        ),
        flush=True,
    )
    op.new()
    book = op.new_book("w", lname="Origin Agent synthetic verification")
    sheet = book[0]
    sheet.from_list(0, [0.0, 1.0, 2.0, 3.0, 4.0], lname="Concentration", units="mmol/L", axis="X")
    sheet.from_list(1, [1.1, 2.9, 5.0, 7.1, 8.9], lname="Absorbance", axis="Y")
    fit = op.LinearFit()
    fit.set_data(sheet, 0, 1)
    result = fit.result()
    print(json.dumps({"parameters": result["Parameters"], "statistics": result["RegStats"]}), flush=True)
    fit2 = op.LinearFit()
    fit2.set_data(sheet, 0, 1)
    report, curve = fit2.report()
    graph = op.new_graph(template="Origin")
    graph[0].add_plot(sheet, colx=0, coly=1, type="s")
    graph[0].add_plot(op.find_sheet("w", curve), colx=0, coly=1, type="l")
    graph[0].rescale()
    graph.save_fig(str(out / "probe.png"), width=1200)
    op.save(str(out / "probe.opju"))
    refs = {"data": sheet.lt_range(), "report": report, "curve": curve, "graph": graph.name}
    del fit, fit2
    op.new()
    opened = op.open(str(out / "probe.opju"))
    refs["reopened"] = bool(opened)
    refs["data_after_reopen"] = op.find_sheet("w", refs["data"]).to_list(1)
    refs["graph_after_reopen"] = op.find_graph(refs["graph"]).name
    refs["seconds"] = round(time.monotonic() - started, 3)
    (out / "probe.json").write_text(json.dumps(refs, indent=2), encoding="utf-8")
    print(json.dumps(refs), flush=True)
finally:
    op.exit()
