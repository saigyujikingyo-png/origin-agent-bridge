"""End-to-end MCP acceptance of the general interfaces against licensed Origin."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

PYTHON_EXAMPLE = """import math
x = [i/10 for i in range(51)]
y = [0.3 + 2.0*math.exp(-v/1.4) for v in x]
w = op.new_sheet('w', lname='Synthetic exponential decay')
w.from_list(0, x, lname='Time', units='s', axis='X')
w.from_list(1, y, lname='Signal', axis='Y')
fit = op.NLFit('ExpDec1')
fit.set_data(w, 0, 1)
for name, value in {'y0':0.2, 'A1':1.8, 't1':1.0}.items():
    fit.set_param(name, value)
fit.fit()
report, curve = fit.report()
params = {name: op.lt_float(f'{fit._get_tree_name()}.{name}') for name in ['y0','A1','t1']}
assert all(abs(params[k]-v) < 1e-4 for k,v in {'y0':0.3,'A1':2.0,'t1':1.4}.items()), params
g = op.new_graph(lname='Synthetic nonlinear fit')
g[0].add_plot(w, colx=0, coly=1, type='s')
g[0].add_plot(op.find_sheet('w', curve), colx=0, coly=1, type='l')
g[0].label('xb').text = 'Time (s)'
g[0].label('yl').text = 'Signal (a.u.)'
g[0].rescale()
RESULTS.update(parameters=params, graph=g.name, report=report, synthetic=True)
del fit
"""


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True)
    parser.add_argument("--exe")
    args = parser.parse_args()
    root = Path(args.home).resolve()
    root.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "ORIGIN_AGENT_HOME": str(root)}
    if args.exe:
        env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
    params = StdioServerParameters(
        command=args.exe or sys.executable,
        args=["serve"] if args.exe else ["-m", "origin_agent", "serve"],
        env=env,
    )
    evidence = {}
    async with Client(params) as client:

        async def call(name, arguments):
            response = await client.call_tool(name, arguments)
            if response.is_error:
                raise RuntimeError(response.content)
            return response.structured_content

        evidence["tools"] = [t.name for t in (await client.list_tools()).tools]
        evidence["capabilities"] = await call("origin_capabilities", {"query": "ExpDec1"})

        async def execute(program):
            job = await call("origin_run_program", {"program": program})
            again = await call("origin_run_program", {"program": program})
            assert again["job_id"] == job["job_id"]
            print(json.dumps({"title": program["title"], "job_id": job["job_id"]}), flush=True)
            while job["state"] not in ("succeeded", "failed", "cancelled", "interrupted"):
                job = await call("origin_get_job", {"job_id": job["job_id"], "wait_seconds": 20})
                print(
                    json.dumps(
                        {
                            "state": job["state"],
                            "progress": job.get("progress"),
                            "error": job.get("error"),
                            "diagnostic": job.get("diagnostic"),
                        }
                    ),
                    flush=True,
                )
            assert job["state"] == "succeeded", job
            result = json.loads((root / "jobs" / job["job_id"] / "result.json").read_text(encoding="utf-8"))
            evidence[program["title"]] = {"job": job, "result": result}
            return job, result

        job, result = await execute(
            {
                "title": "Nonlinear Python",
                "language": "python",
                "code": PYTHON_EXAMPLE,
                "graph_formats": ["png", "pdf", "svg"],
            }
        )
        graph = result["results"]["graph"]
        await execute(
            {
                "title": "Continue OPJU",
                "language": "python",
                "project_artifact": job["job_id"] + "/project.opju",
                "code": f"g=op.find_graph({graph!r})\ng[0].label('xb').text='Time (s), revised'\n"
                "RESULTS['title']=g[0].label('xb').text\n"
                "assert RESULTS['title']=='Time (s), revised'\n",
            }
        )
        _, lt = await execute(
            {
                "title": "LabTalk and X-Functions",
                "language": "labtalk",
                "code": 'newbook name:="LabTalk Test"; wks.ncols=2; wks.nrows=5;\n'
                'col(A)={1,2,3,4,5}; col(B)=col(A)^2; oa_sum=total(col(B));\ntype "total=$(oa_sum)";',
                "readbacks": {"sum": {"expression": "oa_sum", "expected": 55}},
                "graph_formats": [],
            }
        )
        assert "55" in lt["labtalk_output"], lt
        await execute(
            {
                "title": "Origin C compile",
                "revision": "2",
                "language": "origin_c",
                "code": "#include <origin.h>\ndouble oa_square(double x) { return x*x; }\n",
                "entrypoint": "oa_c_value=oa_square(7);",
                "readbacks": {"square": {"expression": "oa_c_value", "expected": 49}},
                "graph_formats": [],
            }
        )
        evidence["host_model_invocation_tested"] = False
        (root / "acceptance-programs.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(json.dumps({"acceptance": str(root / "acceptance-programs.json")}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
