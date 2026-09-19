"""Offline tunnel CLI/process collaborator: real daemons, stdio children and failures."""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import psutil

p = argparse.ArgumentParser()
p.add_argument("--root", type=Path, required=True)
known, args = p.parse_known_args()
root = known.root


def get(flag):
    return args[args.index(flag) + 1]


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def launch(arguments):
    return subprocess.Popen(
        [sys.executable, __file__, "--root", str(root), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


if args[0] in ("run", "serve", "supervise", "controller"):
    write(
        root / "pids" / f"{os.getpid()}.json",
        {
            "pid": os.getpid(),
            "created": psutil.Process().create_time(),
            "role": args[0],
            "profile": get("--profile") if args[0] == "run" else None,
        },
    )
    if args[0] == "controller":
        from origin_agent.storage import file_lock
        from origin_agent.tunnel_lifecycle import Connection, Controller, Policy

        c = Connection.load(get("--config"))
        with file_lock(c.lock, timeout=0):
            controller = Controller(
                c,
                policy=Policy(
                    command_timeout=3,
                    ready_timeout=4,
                    health_interval=0.1,
                    poll=0.05,
                    cleanup_timeout=3,
                    retries=(),
                ),
                command=[sys.executable, __file__, "--root", str(root)],
            )
            controller.supervise()
        raise SystemExit
    if args[0] == "run":
        profile = get("--profile")
        folder = root / profile
        settings = read(folder / "settings.json", {})
        if not settings.get("no_child"):
            child = launch(["serve", "--profile-owner", profile])
            write(folder / "child.json", {"pid": child.pid})
        if settings.get("job_child"):
            launch(["supervise"])
    time.sleep(180)
    raise SystemExit

action = args[1]
alias = get("--alias") if action == "connect" else args[2]
folder = root / alias
settings = read(folder / "settings.json", {})
mapping = read(root / "mapping.json")
profile_dir = mapping[alias]

if action == "connect":
    previous_live = []
    for path in (root / "pids").glob("*.json"):
        item = read(path)
        if item["role"] == "run" and item["profile"] == alias:
            try:
                process = psutil.Process(item["pid"])
                if process.create_time() == item["created"] and process.status() != psutil.STATUS_ZOMBIE:
                    previous_live.append(item["pid"])
            except psutil.NoSuchProcess:
                pass
    events = read(folder / "connect_events.json", [])
    write(folder / "connect_events.json", events + [{"previous_live": previous_live}])
    attempts = read(folder / "connects.json", 0) + 1
    write(folder / "connects.json", attempts)
    if settings.get("before_spawn"):
        raise SystemExit(2)
    child = launch(["run", "--profile-dir", get("--profile-dir"), "--profile", get("--profile")])
    write(folder / "registry.json", {"pid": child.pid, "started": time.time()})
    if settings.get("connect_hang"):
        time.sleep(180)
    if settings.get("after_spawn"):
        time.sleep(0.15)
        raise SystemExit(2)
    print("{}")
elif action == "status":
    if settings.get("status_hang"):
        time.sleep(180)
    if settings.get("status_fail") or (
        settings.get("status_fail_after_spawn") and (folder / "registry.json").exists()
    ):
        raise SystemExit(2)
    registry = read(folder / "registry.json", {})
    running = bool(registry) and psutil.pid_exists(registry["pid"])
    ready = running and time.time() - registry["started"] >= settings.get("ready_after", 0.1)
    if settings.get("unhealthy"):
        ready = False
    meta = {
        "pid": registry.get("pid"),
        "profile_name": alias,
        "profile_dir": profile_dir,
        "started_at": datetime.fromtimestamp(registry.get("started", 0), UTC).isoformat(),
    }
    if settings.get("missing_registry"):
        meta = {}
    print(
        json.dumps(
            {
                "profile_name": alias,
                "profile_dir": profile_dir,
                "process": meta,
                "process_running": running,
                "ready": ready,
                "healthy": ready,
            }
        )
    )
else:
    raise SystemExit(2)
