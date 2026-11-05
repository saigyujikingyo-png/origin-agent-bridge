import os
import sys
from pathlib import Path

from origin_agent.stdio_broker import Broker

root = Path(os.environ["ORIGIN_AGENT_HOME"])
raise SystemExit(
    Broker(
        [sys.executable, str(Path(__file__).with_name("stdio_fixture_backend.py"))],
        root,
        "0.2.8",
        idle_seconds=float(os.environ.get("FIXTURE_IDLE", "0.2")),
        diagnostic=root / "bridge-state.json",
        env=os.environ.copy(),
    ).run()
)
