"""Stop detached protocol/transport test servers."""

from __future__ import annotations

import json
import os
import signal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".matrix-server-pids.json"


def main() -> None:
    if not STATE.exists():
        print("no matrix server state")
        return

    state = json.loads(STATE.read_text())
    for name, info in state.items():
        pid = int(info["pid"])
        try:
            os.killpg(pid, signal.SIGTERM)
            print(f"stopped {name} pid={pid}")
        except ProcessLookupError:
            print(f"already stopped {name} pid={pid}")

    STATE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
