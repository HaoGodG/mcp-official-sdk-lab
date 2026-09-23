"""Run the gateway MCP protocol/transport compatibility matrix."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from client.main import request_access

VERSIONS = ("2025-03-26", "2025-06-18", "2025-11-25", "2026-07-28")


@dataclass(frozen=True)
class Case:
    name: str
    protocol: str
    transport: str
    url: str
    token_file: str | None
    action: str = "call"
    expect_success: bool = True


def token_for(version: str, args: argparse.Namespace) -> str:
    return args.token_2026 if version == "2026-07-28" else args.token_2025


def gateway_url(transport: str, server_version: str) -> str:
    if transport == "streamable-http":
        return f"http://127.0.0.1:8080/py/http/{server_version}"
    return f"http://127.0.0.1:8080/py/sse/{server_version}/sse"


def make_invalid_token(source: str) -> str:
    token = Path(source).read_text().strip()
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("JWT must have three segments")
    signature = parts[2]
    index = len(signature) // 2
    replacement = "A" if signature[index] != "A" else "B"
    parts[2] = signature[:index] + replacement + signature[index + 1 :]
    path = ROOT / ".matrix-invalid.jwt"
    path.write_text(".".join(parts))
    return str(path)


def run_case(case: Case, python_bin: str) -> dict[str, object]:
    cmd = [
        python_bin,
        "-m",
        "client.main",
        "--protocol",
        case.protocol,
        "--transport",
        case.transport,
        "--url",
        case.url,
        "--action",
        case.action,
    ]
    if case.token_file:
        cmd.extend(["--token-file", case.token_file])
    else:
        cmd.extend(["--auth-profile", "none"])
    if case.action == "call":
        cmd.extend(["--tool", "get_protocol_info", "--args", "{}"])

    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=40,
    )
    observed_success = proc.returncode == 0
    passed = observed_success == case.expect_success
    return {
        "name": case.name,
        "expected": "PASS" if case.expect_success else "FAIL",
        "observed": "PASS" if observed_success else "FAIL",
        "result": "PASS" if passed else "FAIL",
        "returnCode": proc.returncode,
        "stdoutTail": "\n".join(proc.stdout.splitlines()[-14:]),
        "stderrTail": "\n".join(proc.stderr.splitlines()[-14:]),
    }


def build_cases(args: argparse.Namespace, invalid_token: str) -> list[Case]:
    cases: list[Case] = []

    for version in VERSIONS:
        for action in ("list", "call"):
            cases.append(
                Case(
                    name=f"http {version} -> {version} {action}",
                    protocol=version,
                    transport="streamable-http",
                    url=gateway_url("streamable-http", version),
                    token_file=token_for(version, args),
                    action=action,
                    expect_success=True,
                )
            )

    for version in VERSIONS[:-1]:
        for action in ("list", "call"):
            cases.append(
                Case(
                    name=f"sse {version} -> {version} {action}",
                    protocol=version,
                    transport="sse",
                    url=gateway_url("sse", version),
                    token_file=token_for(version, args),
                    action=action,
                    expect_success=True,
                )
            )

    cases.append(
        Case(
            name="sse 2026-07-28 -> 2026-07-28 rejected",
            protocol="2026-07-28",
            transport="sse",
            url=gateway_url("sse", "2026-07-28"),
            token_file=args.token_2026,
            action="list",
            expect_success=False,
        )
    )

    for client_version in VERSIONS:
        for server_version in VERSIONS:
            if client_version == server_version:
                continue
            cases.append(
                Case(
                    name=f"cross http {client_version} -> {server_version}",
                    protocol=client_version,
                    transport="streamable-http",
                    url=gateway_url("streamable-http", server_version),
                    token_file=token_for(client_version, args),
                    action="list",
                    expect_success=False,
                )
            )

    cases.extend(
        [
            Case(
                name="http client -> sse endpoint rejected",
                protocol="2025-11-25",
                transport="streamable-http",
                url=gateway_url("sse", "2025-11-25"),
                token_file=args.token_2025,
                expect_success=False,
            ),
            Case(
                name="sse client -> http endpoint rejected",
                protocol="2025-11-25",
                transport="sse",
                url=gateway_url("streamable-http", "2025-11-25"),
                token_file=args.token_2025,
                expect_success=False,
            ),
            Case(
                name="missing token rejected by gateway",
                protocol="2025-11-25",
                transport="streamable-http",
                url=gateway_url("streamable-http", "2025-11-25"),
                token_file=None,
                action="list",
                expect_success=False,
            ),
            Case(
                name="tampered token rejected by gateway",
                protocol="2025-11-25",
                transport="streamable-http",
                url=gateway_url("streamable-http", "2025-11-25"),
                token_file=invalid_token,
                action="list",
                expect_success=False,
            ),
        ]
    )
    return cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--json-output", default=str(ROOT / "matrix-results.json"))
    args = parser.parse_args()

    issued_2025 = request_access("2025")
    issued_2026 = request_access("2026")
    if issued_2025["token"] == issued_2026["token"]:
        raise SystemExit("tokenApply returned identical JWTs for 2025 and 2026 profiles")

    token_2025_path = ROOT / ".matrix-2025.jwt"
    token_2026_path = ROOT / ".matrix-2026.jwt"
    token_2025_path.write_text(issued_2025["token"])
    token_2026_path.write_text(issued_2026["token"])
    args.token_2025 = str(token_2025_path)
    args.token_2026 = str(token_2026_path)

    print(
        "TOKEN_APPLY "
        + json.dumps(
            {
                "2025": {
                    "userId": issued_2025["userId"],
                    "fingerprint": issued_2025["fingerprint"],
                    "mcpServerIds": issued_2025["mcpServerIds"],
                },
                "2026": {
                    "userId": issued_2026["userId"],
                    "fingerprint": issued_2026["fingerprint"],
                    "mcpServerIds": issued_2026["mcpServerIds"],
                },
                "different": issued_2025["token"] != issued_2026["token"],
            },
            ensure_ascii=False,
        )
    )

    invalid_token = make_invalid_token(args.token_2025)
    results = []
    for case in build_cases(args, invalid_token):
        result = run_case(case, args.python)
        results.append(result)
        print(
            f"[{result['result']}] {result['name']} "
            f"expected={result['expected']} observed={result['observed']}"
        )

    summary = {
        "total": len(results),
        "passed": sum(1 for r in results if r["result"] == "PASS"),
        "failed": sum(1 for r in results if r["result"] == "FAIL"),
        "results": results,
    }
    Path(args.json_output).write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: summary[k] for k in ("total", "passed", "failed")}, indent=2))
    raise SystemExit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
