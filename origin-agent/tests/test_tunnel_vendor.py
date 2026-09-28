"""Opt-in real official client acceptance, confined to disposable loopback fixtures."""

import json
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import psutil
import pytest

from origin_agent.storage import write_json
from origin_agent.tunnel_dependency import EXECUTABLE_SHA256
from origin_agent.tunnel_lifecycle import Connection, Controller, Policy

CLIENT = os.environ.get("ORIGIN_TEST_TUNNEL_CLIENT")
pytestmark = pytest.mark.skipif(not CLIENT, reason="requires the pinned official client fixture")


@pytest.fixture
def real_world(tmp_path, monkeypatch):
    from origin_agent.storage import sha256

    client = Path(CLIENT).resolve()
    assert sha256(client) == EXECUTABLE_SHA256
    python = Path(psutil.Process().exe()).resolve()
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(sys.path))
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "sk-isolated-fixture-no-real-credential")
    monkeypatch.delenv("OPENAI_ADMIN_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    requests = []

    class Plane(BaseHTTPRequestHandler):
        def handle_request(self):
            requests.append(self.command)
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(min(length, 1024 * 1024))
            time.sleep(0.02)
            self.send_response(404 if self.command == "GET" else 204)
            self.end_headers()

        do_GET = do_POST = handle_request

        def log_message(self, *_args):
            pass

    plane = ThreadingHTTPServer(("127.0.0.1", 0), Plane)
    thread = threading.Thread(target=plane.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{plane.server_port}"
    monkeypatch.setenv("CONTROL_PLANE_BASE_URL", url)
    script = tmp_path / "isolated_mcp.py"
    script.write_text(
        "from mcp.server.mcpserver import MCPServer\n"
        "server = MCPServer('isolated-fixture')\n"
        "@server.tool()\n"
        "def echo(value: str) -> str:\n"
        "    return value\n"
        "from pathlib import Path\n"
        "import os\n"
        "Path(__file__).with_name('ready-' + str(os.getpid())).write_text('ready')\n"
        "server.run()\n",
        encoding="utf-8",
    )
    state = tmp_path / "state"
    write_json(state / "install.json", {"executable": str(python), "version": "fixture"})
    controllers = []

    def make_controller():
        name = "origin-test-" + uuid.uuid4().hex[:12]
        cloud = state / "cloud/accounts" / name
        config = cloud / "runtime-config.json"
        profile_dir = cloud / "profiles"
        write_json(
            config,
            {
                "schema_version": 2,
                "alias": name,
                "profile": name,
                "profile_dir": str(profile_dir),
                "cloud_root": str(cloud),
                "state_root": str(state),
                "secret_file": str(cloud / "unused.dpapi"),
                "tunnel_client": str(client),
                "client_state_dir": str(cloud / "tunnel-state"),
            },
        )
        write_json(
            profile_dir / f"{name}.yaml",
            {"control_plane": {"tunnel_id": "tunnel_" + "a" * 32, "api_key": "env:CONTROL_PLANE_API_KEY"}},
        )
        controller = Controller(
            Connection.load(config),
            policy=Policy(
                command_timeout=30,
                ready_timeout=30,
                cleanup_timeout=8,
                retries=(),
                recovery_delays=(),
                jitter=0,
            ),
        )
        original = controller.command_json

        def invoke(args, **kwargs):
            args = list(args)
            if args[:2] == ["runtimes", "connect"]:
                args[args.index("--mcp-command") + 1] = f'"{python.as_posix()}" "{script.as_posix()}" serve'
                args += ["--control-plane-base-url", url]
            return original(args, **kwargs)

        controller.command_json = invoke
        controllers.append(controller)
        return controller

    try:
        yield make_controller, requests
    finally:
        # Independent fixture-only teardown is available even when the code under test refuses cleanup.
        # Require the exact executable and a generated path before capturing/rechecking creation time.
        owners = []
        for process in psutil.process_iter(["cmdline"]):
            try:
                argv = process.info["cmdline"] or []
                scoped = str(script) in argv or script.as_posix() in argv
                if "--profile-dir" in argv:
                    path = Path(argv[argv.index("--profile-dir") + 1]).resolve()
                    scoped |= path.is_relative_to(tmp_path.resolve())
                if scoped and Path(process.exe()).resolve() in (client, python):
                    owners.append((process, process.create_time()))
                    process.suspend()
            except psutil.NoSuchProcess:
                pass
        for process, created in owners:
            try:
                if process.create_time() == created:
                    process.kill()
                    process.wait(5)
            except psutil.NoSuchProcess:
                pass
        plane.shutdown()
        plane.server_close()
        thread.join(3)


def test_pinned_client_two_accounts_register_and_cleanup_independently(real_world):
    make, requests = real_world
    first, second = make(), make()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(controller.ensure_ready) for controller in (first, second)]
        a, b = [future.result(timeout=60) for future in futures]
    assert a.live() and b.live()
    for controller, owner in ((first, a), (second, b)):
        status = controller.probe()
        assert status["process"]["pid"] == owner.pid
        assert controller.verified_ready(status, *controller.scan())
        # The vendor's early transport health must not hide a fixture import failure.
        deadline = time.monotonic() + 10
        while True:
            children = controller.scan()[1]
            marker_root = controller.c.state_root.parent
            if children and all((marker_root / ("ready-" + str(p.pid))).exists() for p in children):
                break
            assert time.monotonic() < deadline and owner.live()
            time.sleep(0.05)
        record = json.loads((controller.c.client_state_dir / "processes.yaml").read_text())
        assert set(record) == {controller.c.alias}
    first_pids = {p.pid for p in sum(first.scan(), [])}
    second_pids = {p.pid for p in sum(second.scan(), [])}
    assert first_pids.isdisjoint(second_pids), (first_pids, second_pids)
    terminate = first.terminate

    def bounded_terminate(identity):
        assert identity.pid in first_pids, (identity, first_pids, second_pids)
        return terminate(identity)

    first.terminate = bounded_terminate
    first.reconcile()
    assert not a.live() and b.live()
    assert second.verified_ready(second.probe(), *second.scan())
    second.reconcile()
    assert not b.live()
    assert requests  # Real client reached only the disposable loopback control plane.


def test_pinned_client_refused_cleanup_resumes_its_owned_processes(real_world, monkeypatch):
    from origin_agent.tunnel_lifecycle import OwnershipError

    make, _ = real_world
    controller = make()
    owner = controller.ensure_ready()
    children = controller.scan()[1]

    def refuse(_identity):
        raise OwnershipError("owned_process_did_not_stop")

    original = controller.terminate
    monkeypatch.setattr(controller, "terminate", refuse)
    with pytest.raises(OwnershipError, match="owned_process_did_not_stop"):
        controller.reconcile()
    assert owner.live() and all(child.live() for child in children)
    assert controller.verified_ready(controller.probe(), *controller.scan())
    monkeypatch.setattr(controller, "terminate", original)
    controller.reconcile()
    assert not owner.live()
