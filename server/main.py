"""Strict-version MCP official Python SDK test server."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Literal

from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.server.mcpserver import Context, MCPServer
from mcp.shared.exceptions import MCPError
from mcp.types import UNSUPPORTED_PROTOCOL_VERSION

ProtocolVersion = Literal[
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
    "2026-07-28",
]
Transport = Literal["streamable-http", "sse"]

SUPPORTED_PROTOCOLS: tuple[str, ...] = (
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
    "2026-07-28",
)


class ProtocolGate:
    """Make one server process accept exactly one protocol revision."""

    def __init__(self, protocol: ProtocolVersion, transport: Transport) -> None:
        self.protocol = protocol
        self.transport = transport

    async def __call__(
        self,
        ctx: ServerRequestContext[Any, Any],
        call_next: CallNext,
    ) -> HandlerResult:
        actual = ctx.protocol_version
        if ctx.method == "initialize" and ctx.params is not None:
            requested = ctx.params.get("protocolVersion")
            if isinstance(requested, str):
                actual = requested

        if self.transport == "sse" and self.protocol == "2026-07-28":
            raise MCPError(
                code=UNSUPPORTED_PROTOCOL_VERSION,
                message="MCP 2026-07-28 requires Streamable HTTP in this conformance lab",
                data={"supported": []},
            )

        if actual != self.protocol:
            raise MCPError(
                code=UNSUPPORTED_PROTOCOL_VERSION,
                message=(
                    f"This server process only accepts MCP {self.protocol}; "
                    f"received {actual}"
                ),
                data={"supported": [self.protocol]},
            )

        return await call_next(ctx)


def build_server(protocol: ProtocolVersion, transport: Transport) -> MCPServer:
    server = MCPServer(
        f"mcp-official-python-{transport}-{protocol}",
        instructions=f"Strict MCP {protocol} / {transport} conformance server.",
        middleware=[ProtocolGate(protocol, transport)],
    )

    @server.tool()
    async def echo(text: str, ctx: Context) -> str:
        """Echo text and report the exact protocol/transport/process used."""
        return json.dumps(
            {
                "echo": text,
                "configured_protocol": protocol,
                "protocol_version": ctx.request_context.protocol_version,
                "transport": transport,
                "process_id": os.getpid(),
            },
            ensure_ascii=False,
        )

    @server.tool()
    async def get_protocol_info(ctx: Context) -> str:
        """Return exact configured/negotiated protocol information."""
        return json.dumps(
            {
                "configured_protocol": protocol,
                "protocol_version": ctx.request_context.protocol_version,
                "transport": transport,
                "process_id": os.getpid(),
            },
            ensure_ascii=False,
        )

    return server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strict MCP protocol matrix server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--protocol", choices=SUPPORTED_PROTOCOLS, required=True)
    parser.add_argument(
        "--transport",
        choices=("streamable-http", "sse"),
        default="streamable-http",
    )
    parser.add_argument(
        "--base-path",
        default="",
        help="SSE only: public/gateway prefix used for both /sse and /messages/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    protocol: ProtocolVersion = args.protocol
    transport: Transport = args.transport
    server = build_server(protocol, transport)

    if transport == "streamable-http":
        endpoint = f"http://{args.host}:{args.port}/mcp"
        print(
            f"[mcp-server] pid={os.getpid()} protocol={protocol} "
            f"transport={transport} endpoint={endpoint}",
            flush=True,
        )
        server.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            streamable_http_path="/mcp",
        )
        return

    base_path = args.base_path.rstrip("/")
    sse_path = f"{base_path}/sse" if base_path else "/sse"
    message_path = f"{base_path}/messages/" if base_path else "/messages/"
    print(
        f"[mcp-server] pid={os.getpid()} protocol={protocol} transport=sse "
        f"sse=http://{args.host}:{args.port}{sse_path} "
        f"messages={message_path}",
        flush=True,
    )
    server.run(
        transport="sse",
        host=args.host,
        port=args.port,
        sse_path=sse_path,
        message_path=message_path,
    )


if __name__ == "__main__":
    main()
