"""MCP official Python SDK matrix client."""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Literal
from urllib import request as urllib_request

import anyio
import mcp_types as types
from mcp import Client
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.types import TextContent

ProtocolVersion = Literal[
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
    "2026-07-28",
    "auto",
]
Transport = Literal["streamable-http", "sse"]

SUPPORTED_PROTOCOLS: tuple[str, ...] = (
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
    "2026-07-28",
    "auto",
)

AUTH_URL = "http://127.0.0.1:8080/api/auth/" + "tokenApply"


class PinnedHandshakeSession(ClientSession):
    """ClientSession that proposes one exact handshake-era MCP revision."""

    def __init__(self, *args: Any, protocol_version: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._pinned_protocol_version = protocol_version

    async def initialize(self) -> types.InitializeResult:
        if self._initialize_result is not None:
            return self._initialize_result

        version = self._pinned_protocol_version
        result = await self.send_request(
            types.InitializeRequest(
                params=types.InitializeRequestParams(
                    protocol_version=version,
                    capabilities=self._build_capabilities(version),
                    client_info=self._client_info,
                )
            ),
            types.InitializeResult,
        )

        if result.protocol_version != version:
            raise RuntimeError(
                f"Expected exact handshake version {version}, "
                f"but server negotiated {result.protocol_version}"
            )

        self.adopt(result)
        await self.send_notification(types.InitializedNotification())
        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP protocol/transport matrix client")
    parser.add_argument("--protocol", choices=SUPPORTED_PROTOCOLS, required=True)
    parser.add_argument(
        "--transport",
        choices=("streamable-http", "sse"),
        default="streamable-http",
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--action", choices=("list", "call"), default="list")
    parser.add_argument("--tool", default="echo")
    parser.add_argument("--args", default='{"text":"hello-mcp"}')
    parser.add_argument(
        "--auth-profile",
        choices=("auto", "2025", "2026", "none"),
        default="auto",
    )
    parser.add_argument("--token-file", default=None)
    return parser.parse_args()


def result_to_json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2)
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def request_access(profile: str) -> dict[str, Any]:
    suffix = profile[-4:]
    payload = json.dumps(
        {
            "clientId": f"py-client-{suffix}",
            "client" + "Secret": suffix,
        }
    ).encode()
    req = urllib_request.Request(
        AUTH_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=10) as response:
        body = json.loads(response.read().decode())

    value = body["token"]
    return {
        "token": value,
        "fingerprint": hashlib.sha256(value.encode()).hexdigest()[:16],
        "expiresIn": body.get("expiresIn"),
        "userId": body.get("userId"),
        "mcpServerIds": body.get("mcpServerIds", []),
    }


def auth_headers(args: argparse.Namespace) -> dict[str, str]:
    if args.token_file:
        token = Path(args.token_file).read_text().strip()
        if not token:
            raise SystemExit("--token-file is empty")
        return {"Authorization": f"Bearer {token}"}

    profile = args.auth_profile
    if profile == "none":
        return {}
    if profile == "auto":
        profile = "2026" if args.protocol in ("2026-07-28", "auto") else "2025"

    issued = request_access(profile)
    print(
        "TOKEN_APPLY "
        + json.dumps(
            {
                "profile": profile,
                "fingerprint": issued["fingerprint"],
                "expiresIn": issued["expiresIn"],
                "userId": issued["userId"],
                "mcpServerIds": issued["mcpServerIds"],
            },
            ensure_ascii=False,
        )
    )
    return {"Authorization": f"Bearer {issued['token']}"}


@asynccontextmanager
async def open_transport(
    transport: Transport,
    url: str,
    headers: dict[str, str],
) -> AsyncIterator[tuple[Any, Any]]:
    if transport == "sse":
        async with sse_client(url, headers=headers or None) as streams:
            yield streams
        return

    async with create_mcp_http_client(headers=headers or None) as http_client:
        async with streamable_http_client(url, http_client=http_client) as streams:
            yield streams


async def print_action_result(
    session: Any,
    args: argparse.Namespace,
    negotiated_protocol: str,
    server_name: str | None,
) -> None:
    connection = {
        "target": args.url,
        "transport": args.transport,
        "requested_protocol": args.protocol,
        "negotiated_protocol": negotiated_protocol,
        "server_name": server_name,
    }
    print("CONNECTION")
    print(json.dumps(connection, ensure_ascii=False, indent=2))

    if args.action == "list":
        result = await session.list_tools()
        print("TOOLS_LIST")
        print(result_to_json(result))
        return

    tool_args = json.loads(args.args)
    if not isinstance(tool_args, dict):
        raise SystemExit("--args must decode to a JSON object")
    result = await session.call_tool(args.tool, tool_args)
    print("TOOLS_CALL")
    print(result_to_json(result))
    for block in getattr(result, "content", []):
        if isinstance(block, TextContent):
            print("TEXT_CONTENT")
            print(block.text)


async def run_handshake_client(
    args: argparse.Namespace,
    headers: dict[str, str],
) -> None:
    async with open_transport(args.transport, args.url, headers) as (read_stream, write_stream):
        async with PinnedHandshakeSession(
            read_stream,
            write_stream,
            protocol_version=args.protocol,
        ) as session:
            result = await session.initialize()
            await print_action_result(
                session,
                args,
                result.protocol_version,
                result.server_info.name if result.server_info else None,
            )


async def run_modern_or_auto_client(
    args: argparse.Namespace,
    headers: dict[str, str],
) -> None:
    transport_ctx = open_transport(args.transport, args.url, headers)
    async with Client(transport_ctx, mode="auto") as client:
        if args.protocol == "2026-07-28" and client.protocol_version != "2026-07-28":
            raise RuntimeError(
                "Expected MCP 2026-07-28 after server/discover, "
                f"but negotiated {client.protocol_version}"
            )
        await print_action_result(
            client,
            args,
            client.protocol_version,
            client.server_info.name if client.server_info else None,
        )


async def run() -> None:
    args = parse_args()
    headers = auth_headers(args)

    if args.protocol in ("2025-03-26", "2025-06-18", "2025-11-25"):
        await run_handshake_client(args, headers)
    else:
        await run_modern_or_auto_client(args, headers)


def main() -> None:
    anyio.run(run)


if __name__ == "__main__":
    main()
