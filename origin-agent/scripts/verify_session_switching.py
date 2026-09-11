"""Native acceptance for visible sessions, project switching, and batch coexistence."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--exe")
    args = parser.parse_args()
    root = args.home.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / "sessions").exists() and any((root / "sessions").iterdir()):
        raise ValueError("Use a new test directory")
    env = {**os.environ, "ORIGIN_AGENT_HOME": str(root), "ORIGIN_AGENT_SESSION_IDLE_SECONDS": "3"}
    if args.exe:
        env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
    params = StdioServerParameters(
        command=args.exe or sys.executable,
        args=["serve"] if args.exe else ["-m", "origin_agent", "serve"],
        env=env,
    )
    evidence = {"cases": [], "ok": False, "host_model_invocation_tested": False}
    async with Client(params) as client:

        async def tool(name, arguments):
            response = await client.call_tool(name, arguments)
            assert not response.is_error, response.content
            return response.structured_content

        async def completed(name, arguments, expected="succeeded"):
            job = await tool(name, arguments)
            while job["state"] not in ("succeeded", "failed", "cancelled", "interrupted"):
                job = await tool("origin_get_job", {"job_id": job["job_id"], "wait_seconds": 20})
            evidence["cases"].append(job)
            (root / "acceptance-switching.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            print(json.dumps({"name": name, "state": job["state"], "error": job["error"]}), flush=True)
            assert job["state"] == expected, job
            return job

        async def control(action, key, session=None, **extra):
            values = {"action": action, "request_id": key, **extra}
            if session:
                values.update(session_id=session["session_id"], expected_revision=session["revision"])
            return await completed("origin_session", values)

        async def run(title, code, session=None, expected="succeeded"):
            values = {"program": {"title": title, "language": "python", "code": code, "graph_formats": []}}
            if session:
                values.update(session_id=session["session_id"], expected_revision=session["revision"])
            return await completed("origin_run_program", values, expected)

        first = (await control("open", "first", title="Session A"))["session"]
        first_job = await run("initialize A", "w=op.new_sheet('w')\nw.from_list(0,[1,2,3])", first)
        first = first_job["session"]
        await run(
            "ordinary Save before failure",
            "op.find_sheet('w').from_list(0,[99,99,99])\nop.save()\nraise RuntimeError('saved bad edit')",
            first,
            "failed",
        )
        first = (
            await run("verify rollback after Save", "assert op.find_sheet('w').to_list(0)==[1,2,3]", first)
        )["session"]
        second = (await control("open", "second", title="Session B", visible=True))["session"]
        second = (await run("initialize B", "w=op.new_sheet('w')\nw.from_list(0,[4,5,6])", second))["session"]
        before = await tool("origin_session", {"action": "inspect", "session_id": second["session_id"]})
        await asyncio.sleep(6)
        after = await tool("origin_session", {"action": "inspect", "session_id": second["session_id"]})
        assert after["state"] == "ready" and after["origin_pid"] == before["origin_pid"]
        evidence["visible_session_retained"] = True
        await completed(
            "origin_session",
            {
                "action": "restore",
                "session_id": second["session_id"],
                "expected_revision": second["revision"],
                "request_id": "wrong-session",
                "checkpoint_id": first_job["job_id"],
            },
            "failed",
        )
        await run(
            "independent batch", "w=op.new_sheet('w')\nw.from_list(0,[7,8,9])\nassert sum(w.to_list(0))==24"
        )
        second = (await run("B survives batch", "assert op.find_sheet('w').to_list(0)==[4,5,6]", second))[
            "session"
        ]
        first = (await run("A survives switching", "assert op.find_sheet('w').to_list(0)==[1,2,3]", first))[
            "session"
        ]
        await control("close", "close-first", first)
        await control("close", "close-second", second)
        evidence.update(
            ok=True,
            saved_error_rollback_verified=True,
            separate_project_data_verified=True,
            independent_batch_coexistence_verified=True,
            wrong_checkpoint_rejected=True,
        )
        (root / "acceptance-switching.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(json.dumps({"acceptance": str(root / "acceptance-switching.json")}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
