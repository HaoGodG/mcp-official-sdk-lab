"""Independent MCP official Python SDK client.

Examples:
    python -m client.main --protocol 2025 --action list
    python -m client.main --protocol 2026-07-28 --action list
    python -m client.main --protocol 2025 --action call --tool echo --args '{"text":"hello"}'
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Literal

import anyio
from mcp import Client
from mcp.types import TextContent

ProtocolMode = Literal["2025", "2026-07-28", "auto"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP official Python SDK test client")
    parser.add_argument(
        "--protocol",
        choices=("2025", "2026-07-28", "auto"),
        default="2025",
        help="2025 forces the initialize handshake; 2026-07-28 uses the modern protocol; auto probes server/discover then falls back.",
    )
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    parser.add_argument("--action", choices=("list", "call"), default="list")
    parser.add_argument("--tool", default="echo")
    parser.add_argument("--args", default='{"text":"hello-mcp"}')
    return parser.parse_args()


def sdk_mode(protocol: ProtocolMode) -> str:
    if protocol == "2025":
        return "legacy"
    # For the explicit 2026 test we deliberately use auto instead of a direct
    # version pin, because auto actually sends server/discover. After connect
    # we assert that negotiation landed on 2026-07-28.
    return "auto"


def result_to_json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2)
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


async def run() -> None:
    args = parse_args()
    protocol: ProtocolMode = args.protocol
    mode = sdk_mode(protocol)

    try:
        tool_args = json.loads(args.args)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--args must be valid JSON: {exc}") from exc

    if not isinstance(tool_args, dict):
        raise SystemExit("--args must decode to a JSON object")

    async with Client(args.url, mode=mode) as client:
        if protocol == "2026-07-28" and client.protocol_version != "2026-07-28":
            raise RuntimeError(
                "Expected MCP 2026-07-28 after server/discover, "
                f"but negotiated {client.protocol_version}"
            )

        connection = {
            "target": args.url,
            "requested_mode": protocol,
            "sdk_mode": mode,
            "negotiated_protocol": client.protocol_version,
            "server_name": client.server_info.name if client.server_info else None,
            "server_version": client.server_info.version if client.server_info else None,
        }
        print("CONNECTION")
        print(json.dumps(connection, ensure_ascii=False, indent=2))

        if args.action == "list":
            result = await client.list_tools()
            print("TOOLS_LIST")
            print(result_to_json(result))
            return

        result = await client.call_tool(args.tool, tool_args)
        print("TOOLS_CALL")
        print(result_to_json(result))

        for block in result.content:
            if isinstance(block, TextContent):
                print("TEXT_CONTENT")
                print(block.text)


def main() -> None:
    anyio.run(run)


if __name__ == "__main__":
    main()
