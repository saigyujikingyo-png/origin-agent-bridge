"""Small diagnostic/host entrypoint; no model-provider account is required."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .storage import Store


def main():
    parser = argparse.ArgumentParser(prog="origin-agent")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    serve.add_argument("--port", type=int, default=8765)
    sub.add_parser("status")
    inspect = sub.add_parser("inspect")
    inspect.add_argument("path")
    inspect.add_argument("--sheet")
    plan = sub.add_parser("plan")
    plan.add_argument("file")
    run = sub.add_parser("run")
    run.add_argument("plan_id")
    program = sub.add_parser("program", help="Run a general trusted Origin program from a JSON specification")
    program.add_argument("file")
    caps = sub.add_parser("capabilities")
    caps.add_argument("query", nargs="?", default="")
    caps.add_argument("--detail-id")
    status = sub.add_parser("job")
    status.add_argument("job_id")
    stop = sub.add_parser("cancel")
    stop.add_argument("job_id")
    worker = sub.add_parser("worker")
    worker.add_argument("job_id")
    worker.add_argument("plan_id")
    session_worker = sub.add_parser("session-worker")
    session_worker.add_argument("runtime_dir", type=Path)
    session_worker.add_argument("parent_pid", type=int)
    session_worker.add_argument("parent_created", type=float)
    sub.add_parser("supervise")
    args = parser.parse_args()
    store = Store()
    try:
        if args.command == "serve":
            from .server import make_server

            server = make_server(store)
            if args.transport == "stdio":
                server.run()
            else:
                # Local/tunnel endpoint. Public deployment requires an authenticated gateway.
                server.run(
                    "streamable-http",
                    host="127.0.0.1",
                    port=args.port,
                    stateless_http=True,
                    json_response=True,
                    max_request_body_size=1024 * 1024,
                )
            return
        if args.command == "status":
            from .discovery import discover

            result = {"plugin_version": __version__, **discover(), "home": str(store.root)}
        elif args.command == "inspect":
            from .datasets import inspect_dataset

            result = inspect_dataset(store, args.path, args.sheet)
        elif args.command == "plan":
            from .models import Workflow
            from .planning import plan_workflow

            result = plan_workflow(
                store, Workflow.model_validate_json(Path(args.file).read_text(encoding="utf-8"))
            )
        elif args.command == "run":
            from .jobs import submit

            result = submit(store, args.plan_id)
        elif args.command == "job":
            from .jobs import get_job

            result = get_job(store, args.job_id)
        elif args.command == "program":
            from .jobs import submit
            from .programs import OriginProgram, prepare_program

            spec = OriginProgram.model_validate_json(Path(args.file).read_text(encoding="utf-8-sig"))
            prepared = prepare_program(store, spec)
            result = submit(store, prepared["plan_id"], expected_kind="program")
        elif args.command == "capabilities":
            from .capabilities import capabilities

            result = capabilities(args.query, detail_id=args.detail_id)
        elif args.command == "cancel":
            from .jobs import cancel

            result = cancel(store, args.job_id)
        elif args.command == "worker":
            from .native import run_native
            from .planning import load_plan
            from .program_native import run_program

            target = run_program if load_plan(store, args.plan_id).get("kind") == "program" else run_native
            target(store, args.job_id, args.plan_id)
            return
        elif args.command == "session-worker":
            from .session_native import serve_sessions

            serve_sessions(store, args.runtime_dir, args.parent_pid, args.parent_created)
            return
        elif args.command == "supervise":
            from .jobs import supervise

            supervise(store)
            return
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(
            json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
