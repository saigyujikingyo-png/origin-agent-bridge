"""Real MCP/Origin GUI acceptance on the pinned English Origin 2026b build.

Uses only a new synthetic project. Run in an interactive Windows desktop.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from mcp import Client, StdioServerParameters


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--exe")
    args = parser.parse_args()
    root = args.home.resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("Use a new acceptance directory")
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
    evidence = {"cases": [], "host_model_invocation_tested": False, "ok": False}
    started = time.monotonic()
    sid, revision = None, None
    async with Client(params) as client:

        async def call(name, arguments):
            response = await client.call_tool(name, arguments)
            if response.is_error:
                raise RuntimeError(response.content)
            return response.structured_content

        def record():
            (root / "acceptance-gui.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")

        async def job(name, arguments, label, expected="succeeded"):
            nonlocal revision
            tick = time.monotonic()
            value = await call(name, arguments)
            while value["state"] not in ("succeeded", "failed", "cancelled", "interrupted"):
                if time.monotonic() - tick > 180:
                    raise TimeoutError(label)
                value = await call("origin_get_job", {"job_id": value["job_id"], "wait_seconds": 20})
            if "session" in value:
                revision = value["session"]["revision"]
            elif sid:
                state = await call("origin_session", {"action": "inspect", "session_id": sid})
                revision = state["revision"]
            evidence["cases"].append(
                {
                    "label": label,
                    "seconds": round(time.monotonic() - tick, 3),
                    "expected": expected,
                    "job": value,
                }
            )
            record()
            print(
                json.dumps({"label": label, "state": value["state"], "error": value.get("error")}), flush=True
            )
            assert value["state"] == expected, value
            return value

        async def gui(action, label, expected="succeeded", **fields):
            return await job(
                "origin_gui",
                {
                    "session_id": sid,
                    "expected_revision": revision,
                    "request_id": label,
                    "gui": {"action": action, **fields},
                },
                label,
                expected,
            )

        async def program(label, code, expected="succeeded", standalone=False):
            request = {"program": {"title": label, "language": "python", "code": code, "graph_formats": []}}
            if not standalone:
                request.update(session_id=sid, expected_revision=revision)
            return await job("origin_run_program", request, label, expected)

        def select(view, predicate):
            matches = [node for node in view["gui"]["targets"] if node["enabled"] and predicate(node)]
            assert len(matches) == 1, matches
            return matches[0]["id"]

        async def invoke(view, target, label, query):
            return await gui(
                "invoke", label, observation_id=view["job_id"], target_id=target, query=query, screenshot=True
            )

        async def properties(view, prefix):
            target = select(view, lambda n: n["text"] == "Window" and n.get("role") == 50011)
            menu = await invoke(view, target, prefix + " open Window menu", "Properties")
            target = select(menu, lambda n: n["text"].replace("&", "").startswith("Properties"))
            dialog = await invoke(menu, target, prefix + " open Properties", "Edit")
            assert any(w["text"].startswith("Window Properties") for w in dialog["gui"]["windows"])
            assert dialog["gui"]["blocked"]
            return dialog

        async def set_name(dialog, value, label):
            # Control ID 4216 was observed and visually identified as Long name on the pinned build.
            # Never pass a native handle or dispatch a guessed ID: select the current returned node.
            target = select(dialog, lambda n: n.get("class") == "Edit" and n.get("control_id") == 4216)
            return await gui(
                "set_text",
                label,
                observation_id=dialog["job_id"],
                target_id=target,
                text=value,
                query="OK",
                screenshot=True,
            )

        try:
            opened = await job(
                "origin_session",
                {
                    "action": "open",
                    "request_id": "gui acceptance open",
                    "visible": True,
                    "title": "Origin Companion synthetic GUI acceptance",
                },
                "open synthetic project",
            )
            sid = opened["session"]["session_id"]
            await program(
                "seed synthetic workbook",
                "w=op.new_sheet('w',lname='GUI baseline')\n"
                "w.from_list(0,[1,2,3])\nRESULTS['book']=w.get_book().name",
            )
            view = await gui("begin", "begin GUI transaction", query="Window")
            old_view = view
            view = await gui("observe", "fresh observation", query="Window")
            await gui(
                "invoke",
                "reject stale observation",
                "failed",
                observation_id=old_view["job_id"],
                target_id=select(old_view, lambda n: n["text"] == "Window" and n.get("role") == 50011),
            )
            await program("reject program during GUI", "raise AssertionError('must not run')", "failed")
            await program("reject batch during GUI", "raise AssertionError('must not run')", "failed", True)
            view = await gui("observe", "observe after isolation probes", query="Window")
            dialog = await properties(view, "commit")
            await gui("commit", "reject commit with modal open", "failed")
            edited = await set_name(dialog, "Origin Companion GUI verified", "set workbook long name")
            target = select(edited, lambda n: n.get("class") == "Button" and n.get("control_id") == 1)
            confirmed = await invoke(edited, target, "confirm Properties", "Window")
            if confirmed["gui"]["blocked"]:
                menus = [w for w in confirmed["gui"]["windows"] if w["popup"] and not w["text"]]
                assert len(menus) == 1, confirmed["gui"]
                confirmed = await gui(
                    "dismiss",
                    "dismiss remaining MFC menu",
                    observation_id=confirmed["job_id"],
                    target_id=menus[0]["id"],
                    query="Window",
                    screenshot=True,
                )
            assert not confirmed["gui"]["blocked"]
            await gui("commit", "commit GUI changes", query="Window", screenshot=True)
            verify = (
                "w=op.find_sheet('w')\nRESULTS['long_name']=w.get_book().lname\n"
                "RESULTS['values']=w.to_list(0)\n"
                "assert RESULTS['long_name']=='Origin Companion GUI verified'\n"
                "assert RESULTS['values']==[1,2,3]"
            )
            await program("read back committed name and data", verify)
            view = await gui("begin", "begin rollback transaction", query="Window")
            dialog = await properties(view, "rollback")
            await set_name(dialog, "Uncommitted name to discard", "edit before modal rollback")
            rolled = await gui("rollback", "rollback with modal open", query="Window", screenshot=True)
            assert rolled["verification"]["project_reopened"]
            assert not rolled["gui"]["blocked"]
            await program("read back rollback name and data", verify)
            evidence.update(
                gui_commit_readback=True,
                modal_rollback_readback=True,
                seconds=round(time.monotonic() - started, 3),
            )
        finally:
            if sid:
                state = await call("origin_session", {"action": "inspect", "session_id": sid})
                revision = state["revision"]
                if state.get("gui_transaction_open"):
                    await gui("rollback", "cleanup unfinished GUI transaction")
                await job(
                    "origin_session",
                    {
                        "action": "close",
                        "session_id": sid,
                        "expected_revision": revision,
                        "request_id": "gui acceptance close",
                    },
                    "close synthetic project",
                )
            record()
        evidence.update(ok=True, seconds=round(time.monotonic() - started, 3))
        record()
        print(json.dumps({"acceptance": str(root / "acceptance-gui.json"), "ok": evidence["ok"]}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
