# mcp-official-sdk-lab

独立的 MCP 官方 Python SDK 协议兼容性实验工程，用于验证：

```text
Python Client -> MCP Gateway -> Python Server
```

Client/Server 都基于 `mcp==2.2.0`，并且 Server 按“协议版本 + transport”独立进程启动。

## 覆盖范围

协议版本：

- `2025-03-26`
- `2025-06-18`
- `2025-11-25`
- `2026-07-28`

Transport：

- `streamable-http`
- legacy HTTP+SSE（2025 handshake-era）
- `2026-07-28 + SSE` 保留为预期失败用例

握手：

- 2025 三个版本：精确 `initialize`，不会统一退化成 2025-11-25
- 2026-07-28：真实 `server/discover`
- 每个 Server 只接受自己配置的精确版本

## Server 端口矩阵

| Transport | Protocol | Port |
|---|---|---:|
| Streamable HTTP | 2025-03-26 | 8101 |
| Streamable HTTP | 2025-06-18 | 8102 |
| Streamable HTTP | 2025-11-25 | 8103 |
| Streamable HTTP | 2026-07-28 | 8104 |
| SSE | 2025-03-26 | 8201 |
| SSE | 2025-06-18 | 8202 |
| SSE | 2025-11-25 | 8203 |
| SSE | 2026-07-28 | 8204（negative test） |

启动全部 Server：

```bash
python scripts/start_servers.py
```

停止：

```bash
python scripts/stop_servers.py
```

## Client

精确 2025 版本：

```bash
python -m client.main \
  --protocol 2025-03-26 \
  --transport streamable-http \
  --url http://127.0.0.1:8080/py/http/2025-03-26 \
  --token-file /tmp/matrix-2025.jwt \
  --action call \
  --tool get_protocol_info \
  --args '{}'
```

2026：

```bash
python -m client.main \
  --protocol 2026-07-28 \
  --transport streamable-http \
  --url http://127.0.0.1:8080/py/http/2026-07-28 \
  --token-file /tmp/matrix-2026.jwt \
  --action list
```

SSE：

```bash
python -m client.main \
  --protocol 2025-11-25 \
  --transport sse \
  --url http://127.0.0.1:8080/py/sse/2025-11-25/sse \
  --token-file /tmp/matrix-2025.jwt \
  --action call \
  --tool get_protocol_info \
  --args '{}'
```

## Gateway 路由

Gateway 的 UAT 配置新增 8 条测试路由：

```text
/py/http/2025-03-26
/py/http/2025-06-18
/py/http/2025-11-25
/py/http/2026-07-28

/py/sse/2025-03-26/**
/py/sse/2025-06-18/**
/py/sse/2025-11-25/**
/py/sse/2026-07-28/**
```

Client 内置两套 dev-only tokenApply 身份：

- `py-client-2025`：固定测试参数由 Client 代码生成
- `py-client-2026`：固定测试参数由 Client 代码生成

Gateway 的 `credentials.yml` 只保存对应 SHA-256，`permissions.yml` 为两个身份开放全部 8 条协议矩阵路由。上线前替换这些测试参数。

Client 默认会先调用：

```text
POST http://127.0.0.1:8080/api/auth/tokenApply
```

获得 JWT 后再发 MCP 请求。也可以用 `--auth-profile none` 专门验证无 Token 场景，或用 `--token-file` 复用已有 JWT。

## 自动矩阵

```bash
python scripts/run_matrix.py
```

Runner 会先真实执行两次 tokenApply，确认两枚 JWT 不同，再复用这两枚 Token 跑完整矩阵。

矩阵覆盖：

- 4 个 Streamable HTTP 同版本 `tools/list` + `tools/call`
- 3 个 SSE handshake-era 同版本 `tools/list` + `tools/call`
- 2026 + SSE 预期失败
- 4 个 HTTP 版本的全部 12 个交叉组合，预期失败
- HTTP Client -> SSE endpoint，预期失败
- SSE Client -> HTTP endpoint，预期失败
- 无 Token，预期失败
- 篡改 JWT 签名，预期失败

当前 E2E 基线：

```text
TOTAL: 31
PASS : 31
FAIL : 0
```

## Server Tools

- `echo`
- `get_protocol_info`

`get_protocol_info` 返回：

```json
{
  "configured_protocol": "2025-06-18",
  "protocol_version": "2025-06-18",
  "transport": "streamable-http",
  "process_id": 12345
}
```

用于确认请求经过 Gateway 后，实际到达的协议版本和 transport 没有被改写。
