# mcp-official-sdk-lab

这是一个**独立仓库**，不依赖也不修改原来的 `mcp` 工程。

用途只有两部分：

1. `client`：使用 MCP 官方 Python SDK 发起 MCP 请求，作用类似原来的 Client 测试工程。
2. `server`：使用 MCP 官方 Python SDK 启动一个独立 MCP Server。

Client 和 Server 是两个独立进程。Client 不会在进程内创建或复用 Server 实例。

## 版本

- Python: >= 3.10
- MCP 官方 Python SDK: `mcp==2.2.0`
- 2025 era: 最高到 `2025-11-25`，使用 `initialize`
- 2026 era: `2026-07-28`，使用 modern protocol / `server/discover`

官方 Python SDK 的 Server 在同一个 Streamable HTTP endpoint 上原生兼容两代协议。官方当前没有 Server 端的“只允许 2025”或“只允许 2026”的版本开关，因此这里不伪造该能力。

## 工程结构

```text
mcp-official-sdk-lab/
├── pyproject.toml
├── client/
│   ├── __init__.py
│   └── main.py
└── server/
    ├── __init__.py
    └── main.py
```

## 安装

推荐 uv：

```bash
uv sync
```

也可以使用普通 pip：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 1. 启动独立 Server

终端 A：

```bash
uv run python -m server.main
```

默认地址：

```text
http://127.0.0.1:8000/mcp
```

指定端口：

```bash
uv run python -m server.main --host 127.0.0.1 --port 8100
```

Server 内置两个 Tools：

- `echo`
- `get_protocol_info`

两个 Tool 都会返回当前请求实际使用的 `protocol_version`、协议时代和 Server PID。

## 2. 使用 2025 协议 Client

终端 B：

```bash
uv run python -m client.main \
  --protocol 2025 \
  --url http://127.0.0.1:8000/mcp \
  --action list
```

此模式对应官方 SDK：

```python
Client(url, mode="legacy")
```

它**不会先发 server/discover**，而是直接执行 2025-era 的 `initialize` 握手。

当前官方 SDK 的最新 handshake-era 版本是：

```text
2025-11-25
```

查看 Server 实际识别到的协议：

```bash
uv run python -m client.main \
  --protocol 2025 \
  --action call \
  --tool get_protocol_info \
  --args '{}'
```

## 3. 使用 2026-07-28 Client

```bash
uv run python -m client.main \
  --protocol 2026-07-28 \
  --url http://127.0.0.1:8000/mcp \
  --action list
```

此模式对应：

```python
Client(url, mode="2026-07-28")
```

这是 modern 协议版本。

验证 Tool：

```bash
uv run python -m client.main \
  --protocol 2026-07-28 \
  --action call \
  --tool get_protocol_info \
  --args '{}'
```

返回中应看到：

```json
{
  "protocol_version": "2026-07-28",
  "era": "2026-modern"
}
```

## 4. 自动协商模式

也提供：

```bash
uv run python -m client.main --protocol auto --action list
```

对应：

```python
Client(url)
```

官方 SDK 会先发送 `server/discover`：

- modern Server 响应后采用 `2026-07-28`
- 老 Server 不支持 `server/discover` 时回退到 `initialize`

## tools/call 示例

2025：

```bash
uv run python -m client.main \
  --protocol 2025 \
  --action call \
  --tool echo \
  --args '{"text":"hello-2025"}'
```

2026：

```bash
uv run python -m client.main \
  --protocol 2026-07-28 \
  --action call \
  --tool echo \
  --args '{"text":"hello-2026"}'
```

## 为什么 Server 不提供 --protocol 参数

这是官方 Python SDK v2 的行为，不是本工程限制。

官方 Server 的 Streamable HTTP 入口会按请求自动路由：

- 无 modern version header / handshake-era 请求 -> 2025 legacy 路径
- `MCP-Protocol-Version: 2026-07-28` -> modern 路径

官方目前明确没有 `legacy=`、版本 allowlist 或禁用某个 era 的 Server 配置。

因此本工程用 **Client 的 mode** 明确制造 2025 和 2026 两种请求，再通过 Server Tool 返回的 `ctx.request_context.protocol_version` 验证实际协议版本。
