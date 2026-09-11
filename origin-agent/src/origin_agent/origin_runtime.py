"""Create and identify an owned Origin instance; never attach to unrelated work."""

import contextlib
import os
from pathlib import Path

from .native import origin_processes
from .target import require_target


def release_terminated_origin(runtime):
    """Drop the pinned originpro wrapper's connection only after its owned process exited."""
    import psutil

    with contextlib.suppress(psutil.NoSuchProcess):
        process = psutil.Process(runtime["origin_pid"])
        if abs(process.create_time() - runtime["origin_created"]) < 0.01:
            raise RuntimeError("Cannot reset an Origin connection while its process is alive")
    op = runtime["op"]
    try:
        op.detach()
    except Exception:
        # originpro 1.1.15 APP.Exit does not clear _app when dead-server Exit raises.
        # The process is already gone; reset that local reference for lazy reconnection.
        op.po._app = None


def connect_origin(visible=False):
    import originpro as op

    before = origin_processes()
    try:
        op.set_show(visible)
        engine = {
            "version": op.lt_float("@V"),
            "bitness": op.lt_int("@VB"),
            "edition": "OriginPro" if op.lt_int("@IM") == 2 else "Origin",
            "demo": op.lt_int("@VM"),
            "executable_directory": op.path("e"),
        }
        candidates = [
            p
            for pid, p in origin_processes().items()
            if pid not in before
            and p["exe"]
            and Path(p["exe"]).parent.resolve() == Path(op.path("e")).resolve()
        ]
        if len(candidates) != 1:
            raise RuntimeError("Cannot uniquely identify this owned Origin instance")
        explicit = os.environ.get("ORIGIN_AGENT_EXECUTABLE")
        if explicit and Path(explicit).resolve().parent != Path(op.path("e")).resolve():
            raise RuntimeError("COM activated a different installation; fix registration")
        require_target(engine)
        return {
            "op": op,
            "engine": engine,
            "origin_pid": candidates[0]["pid"],
            "origin_created": candidates[0]["create_time"],
        }
    except Exception:
        with contextlib.suppress(Exception):
            op.exit()
        raise
