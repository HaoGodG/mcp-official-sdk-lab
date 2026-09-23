"""Start all strict protocol/transport test servers as detached processes."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".matrix-server-pids.json"
LOG_DIR = ROOT / ".matrix-logs"

SERVERS = [
    ("http-2025-03-26", 8101, "2025-03-26", "streamable-http", ""),
    ("http-2025-06-18", 8102, "2025-06-18", "streamable-http", ""),
    ("http-2025-11-25", 8103, "2025-11-25", "streamable-http", ""),
    ("http-2026-07-28", 8104, "2026-07-28", "streamable-http", ""),
    ("sse-2025-03-26", 8201, "2025-03-26", "sse", "/py/sse/2025-03-26"),
    ("sse-2025-06-18", 8202, "2025-06-18", "sse", "/py/sse/2025-06-18"),
    ("sse-2025-11-25", 8203, "2025-11-25", "sse", "/py/sse/2025-11-25"),
    ("sse-2026-07-28", 8204, "2026-07-28", "sse", "/py/sse/2026-07-28"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()

    LOG_DIR.mkdir(exist_ok=True)
    processes = {}

    for name, port, protocol, transport, base_path in SERVERS:
        cmd = [
            args.python,
            "-m",
            "server.main",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--protocol",
            protocol,
            "--transport",
            transport,
        ]
        if base_path:
            cmd.extend(["--base-path", base_path])

        log_path = LOG_DIR / f"{name}.log"
        log = log_path.open("ab")
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        processes[name] = {
            "pid": proc.pid,
            "port": port,
            "protocol": protocol,
            "transport": transport,
            "log": str(log_path),
        }

    STATE.write_text(json.dumps(processes, indent=2))
    print(json.dumps(processes, indent=2))


if __name__ == "__main__":
    main()
