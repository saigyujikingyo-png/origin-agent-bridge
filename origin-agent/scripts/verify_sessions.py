"""Real MCP acceptance of continuous editing, rollback, cancel and idle resume."""

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
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--exe")
    args = parser.parse_args()
    root = args.home.resolve()
    if (root / "sessions").exists() and any((root / "sessions").iterdir()):
        raise ValueError("Use a new acceptance directory")
    root.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "ORIGIN_AGENT_HOME": str(root), "ORIGIN_AGENT_SESSION_IDLE_SECONDS": "4"}
    if args.exe:
        env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
    params = StdioServerParameters(
        command=args.exe or sys.executable,
        args=["serve"] if args.exe else ["-m", "origin_agent", "serve"],
        env=env,
    )
    evidence = {"cases": [], "host_model_invocation_tested": False}
    async with Client(params) as client:

        async def call(name, arguments):
            response = await client.call_tool(name, arguments)
            if response.is_error:
                raise RuntimeError(response.content)
            return response.structured_content

        async def wait_job(job, label, expected="succeeded"):
            tick = time.monotonic()
            while job["state"] not in ("succeeded", "failed", "cancelled", "interrupted"):
                job = await call("origin_get_job", {"job_id": job["job_id"], "wait_seconds": 20})
            item = {"label": label, "seconds": round(time.monotonic() - tick, 3), "job": job}
            evidence["cases"].append(item)
            (root / "acceptance-sessions.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            print(json.dumps({"label": label, "state": job["state"], "error": job.get("error")}), flush=True)
            assert job["state"] == expected, job
            return job

        opened = await wait_job(
            await call(
                "origin_session",
                {
                    "action": "open",
                    "request_id": "acceptance-open",
                    "title": "Synthetic continuous editing",
                },
            ),
            "open",
        )
        sid = opened["session"]["session_id"]
        revision = opened["session"]["revision"]

        async def control(action, key, **extra):
            return await wait_job(
                await call(
                    "origin_session",
                    {
                        "action": action,
                        "session_id": sid,
                        "expected_revision": revision,
                        "request_id": key,
                        **extra,
                    },
                ),
                action,
            )

        async def run(title, code, expected="succeeded", use_revision=None, wait=True):
            program = {"title": title, "language": "python", "code": code, "graph_formats": []}
            arguments = {
                "program": program,
                "session_id": sid,
                "expected_revision": revision if use_revision is None else use_revision,
            }
            job = await call("origin_run_program", arguments)
            duplicate = await call("origin_run_program", arguments)
            assert job["job_id"] == duplicate["job_id"]
            return await wait_job(job, title, expected) if wait else job

        created = await run(
            "create worksheet",
            "w=op.new_sheet('w',lname='Session data')\n"
            "w.from_list(0,[1,2,3],axis='X')\nw.from_list(1,[2,4,6])\n"
            "RESULTS['sum']=sum(w.to_list(1))\nassert RESULTS['sum']==12",
        )
        revision = created["session"]["revision"]
        checkpoint_id = created["job_id"]
        initial = await call("origin_session", {"action": "inspect", "session_id": sid})
        first_pid = initial["origin_pid"]
        modified = await run(
            "edit existing worksheet",
            "w=op.find_sheet('w')\nw.from_list(1,[3,6,9])\n"
            "RESULTS['sum']=sum(w.to_list(1))\nassert RESULTS['sum']==18",
        )
        revision = modified["session"]["revision"]
        state = await call("origin_session", {"action": "inspect", "session_id": sid})
        assert state["origin_pid"] == first_pid
        # A second MCP process (representing another host) sees the same committed session.
        async with Client(params) as second_client:
            other = await second_client.call_tool("origin_session", {"action": "inspect", "session_id": sid})
            assert not other.is_error
            assert other.structured_content["revision"] == revision
            assert other.structured_content["origin_pid"] == first_pid
        evidence["second_mcp_process_verified"] = True
        await run("reject stale edit", "raise AssertionError('must not execute')", "failed", use_revision=1)
        state = await call("origin_session", {"action": "inspect", "session_id": sid})
        assert state["revision"] == revision
        failed = await run(
            "rollback failed edit",
            "w=op.find_sheet('w')\nw.from_list(1,[100,200,300])\nop.save()\n"
            "raise RuntimeError('intentional failure after modifying data')",
            "failed",
        )
        assert "intentional failure" in failed["error"]
        checked = await run(
            "read after rollback",
            "RESULTS['sum']=sum(op.find_sheet('w').to_list(1))\nassert RESULTS['sum']==18",
        )
        revision = checked["session"]["revision"]
        restored = await control("restore", "acceptance-restore", checkpoint_id=checkpoint_id)
        revision = restored["session"]["revision"]
        checked = await run(
            "read restored checkpoint",
            "RESULTS['sum']=sum(op.find_sheet('w').to_list(1))\nassert RESULTS['sum']==12",
        )
        revision = checked["session"]["revision"]
        slow = await run(
            "cancel incomplete edit",
            "import time\nw=op.find_sheet('w')\nw.from_list(1,[99,99,99])\ntime.sleep(20)",
            wait=False,
        )
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            slow = await call("origin_get_job", {"job_id": slow["job_id"]})
            if slow.get("progress", {}).get("stage") == "executing_program":
                break
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("Slow operation did not reach execution")
        await call("origin_cancel_job", {"job_id": slow["job_id"]})
        await wait_job(slow, "cancel incomplete edit", "cancelled")
        checked = await run(
            "recover after cancel",
            "RESULTS['sum']=sum(op.find_sheet('w').to_list(1))\nassert RESULTS['sum']==12",
        )
        revision = checked["session"]["revision"]
        current = await call("origin_session", {"action": "inspect", "session_id": sid})
        pid_before_idle = current["origin_pid"]
        await asyncio.sleep(7)
        idle = await call("origin_session", {"action": "inspect", "session_id": sid})
        assert idle["state"] == "suspended", idle
        checked = await run(
            "resume after idle",
            "RESULTS['sum']=sum(op.find_sheet('w').to_list(1))\nassert RESULTS['sum']==12",
        )
        revision = checked["session"]["revision"]
        current = await call("origin_session", {"action": "inspect", "session_id": sid})
        assert current["origin_pid"] != pid_before_idle
        closed = await control("close", "acceptance-close")
        assert closed["session"]["state"] == "closed"
        evidence.update(
            ok=True,
            same_pid_for_continuous_edits=True,
            numerical_rollback_verified=True,
            cancel_recovery_verified=True,
            idle_resume_verified=True,
            request_deduplication_verified=True,
        )
        (root / "acceptance-sessions.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(json.dumps({"acceptance": str(root / "acceptance-sessions.json")}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
