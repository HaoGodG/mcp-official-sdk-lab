"""Independent MCP official Python SDK server.

One HTTP server process serves both MCP protocol eras, as defined by the
official Python SDK:
- 2025 era: initialize handshake
- 2026-07-28 era: modern server/discover path

Run:
    python -m server.main --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import argparse
import json
import os

from mcp.server.mcpserver import Context, MCPServer
from mcp.types.version import MODERN_PROTOCOL_VERSIONS

mcp = MCPServer(
    "mcp-official-python-sdk-server",
    instructions="Independent MCP official Python SDK compatibility server.",
)


@mcp.tool()
async def echo(text: str, ctx: Context) -> str:
    """Echo text and report the protocol version that served this request."""
    protocol_version = ctx.request_context.protocol_version
    era = "2026-modern" if protocol_version in MODERN_PROTOCOL_VERSIONS else "2025-legacy"
    return json.dumps(
        {
            "echo": text,
            "protocol_version": protocol_version,
            "era": era,
            "process_id": os.getpid(),
        },
        ensure_ascii=False,
    )


@mcp.tool()
async def get_protocol_info(ctx: Context) -> str:
    """Return negotiated MCP protocol information for this request."""
    protocol_version = ctx.request_context.protocol_version
    era = "2026-modern" if protocol_version in MODERN_PROTOCOL_VERSIONS else "2025-legacy"
    return json.dumps(
        {
            "protocol_version": protocol_version,
            "era": era,
            "process_id": os.getpid(),
        },
        ensure_ascii=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP official Python SDK server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        f"[mcp-server] pid={os.getpid()} endpoint=http://{args.host}:{args.port}/mcp "
        "protocols=2025-era,2026-07-28"
    )
    mcp.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        streamable_http_path="/mcp",
    )


if __name__ == "__main__":
    main()
