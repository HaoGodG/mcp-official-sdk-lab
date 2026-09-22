# mcp-official-sdk-lab

独立于原有 `mcp` 仓库的 MCP 官方 SDK 验证工程。

工程包含两个完全独立的应用：

- `client`：使用 MCP 官方 TypeScript SDK 发起 MCP 请求，作用类似原有 `mcp-client`
- `server`：使用 MCP 官方 TypeScript SDK 启动 MCP Server

两个应用不会运行在同一个进程或复用同一个 MCP 实例。

## 官方 SDK

使用：

- `@modelcontextprotocol/client` 2.0.0
- `@modelcontextprotocol/server` 2.0.0
- `@modelcontextprotocol/node` 2.0.0
- Node.js >= 20

官方 TypeScript SDK v2 把 MCP 协议分为两代：

- 2025 era：使用 `initialize`
- 2026 era：`2026-07-28`，使用 `server/discover` 和 modern request envelope

## 支持的 MCP 版本

Client 和 Server 都支持：

- `2025-03-26`
- `2025-06-18`
- `2025-11-25`
- `2026-07-28`

## 安装

在工程根目录：

```bash
npm install
```

## 启动 Server

### 2025 独立实例

```bash
npm run server:2025
```

默认：

- protocol: `2025-11-25`
- port: `3100`
- MCP: `http://127.0.0.1:3100/mcp`
- health: `http://127.0.0.1:3100/health`

也可指定其他 2025 版本：

```bash
npm run start --workspace server -- --protocol 2025-06-18 --port 3102
```

### 2026-07-28 独立实例

另开一个终端：

```bash
npm run server:2026
```

默认：

- protocol: `2026-07-28`
- port: `3101`
- MCP: `http://127.0.0.1:3101/mcp`
- health: `http://127.0.0.1:3101/health`

2025 和 2026 Server 是不同 Node 进程、不同 PID、不同端口、不同 MCP Server 实例。

## Client 测试

### 2025 tools/list

```bash
npm run client:2025:list
```

### 2025 tools/call

```bash
npm run start --workspace client -- \
  --protocol 2025-11-25 \
  --url http://127.0.0.1:3100/mcp \
  --action call \
  --tool echo \
  --args '{"text":"hello-2025"}'
```

### 2026-07-28 tools/list

```bash
npm run client:2026:list
```

### 2026-07-28 tools/call

```bash
npm run start --workspace client -- \
  --protocol 2026-07-28 \
  --url http://127.0.0.1:3101/mcp \
  --action call \
  --tool echo \
  --args '{"text":"hello-2026"}'
```

## 验证实例隔离

Server 内置：

- `echo`
- `get-protocol-info`

`get-protocol-info` 返回当前 Server 的：

- `configuredProtocol`
- `processId`

因此可以直接确认 2025 和 2026 请求是否命中了不同实例。

## 版本行为

### 2025

Client 使用：

- `versionNegotiation.mode = legacy`
- `supportedProtocolVersions = [指定的2025版本]`

因此通过 `initialize` 协商并固定具体 2025 版本。

### 2026-07-28

Client 使用：

- `versionNegotiation.mode = { pin: "2026-07-28" }`
- `supportedProtocolVersions = ["2026-07-28"]`

因此不会 fallback 到 2025。

Server 的 2026 实例：

- 只声明 `2026-07-28`
- `createMcpHandler(..., { legacy: "reject" })`
- 接受 `server/discover`
- 拒绝 2025 legacy opening

Server 的 2025 实例：

- 只声明选定的 2025 版本
- 使用 legacy stateless HTTP serving

这样不会出现一个 Server 实例同时承载两代协议的问题。
