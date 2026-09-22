import { createServer } from 'node:http';

import {
  localhostHostValidation,
  localhostOriginValidation,
  toNodeHandler
} from '@modelcontextprotocol/node';

import {
  createMcpHandler,
  McpServer
} from '@modelcontextprotocol/server';

import * as z from 'zod/v4';

type ProtocolVersion =
  | '2025-03-26'
  | '2025-06-18'
  | '2025-11-25'
  | '2026-07-28';

const SUPPORTED_PROTOCOLS = new Set<ProtocolVersion>([
  '2025-03-26',
  '2025-06-18',
  '2025-11-25',
  '2026-07-28'
]);

function readArg(name: string): string | undefined {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

function parseProtocol(value: string): ProtocolVersion {
  if (!SUPPORTED_PROTOCOLS.has(value as ProtocolVersion)) {
    throw new Error(
      `Unsupported --protocol ${value}. Supported: ${[...SUPPORTED_PROTOCOLS].join(', ')}`
    );
  }

  return value as ProtocolVersion;
}

const protocol = parseProtocol(
  readArg('--protocol') ??
    process.env.MCP_PROTOCOL_VERSION ??
    '2025-11-25'
);

const host =
  readArg('--host') ??
  process.env.MCP_HOST ??
  '127.0.0.1';

const port = Number(
  readArg('--port') ??
    process.env.MCP_PORT ??
    (protocol === '2026-07-28' ? '3101' : '3100')
);

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error(`Invalid port: ${port}`);
}

function createProtocolPinnedServer(): McpServer {
  const server = new McpServer(
    {
      name: 'mcp-official-sdk-test-server',
      version: '1.0.0'
    },
    {
      supportedProtocolVersions: [protocol],
      capabilities: {
        tools: {}
      }
    }
  );

  server.registerTool(
    'echo',
    {
      description: 'Echo input and identify the protocol-pinned server instance.',
      inputSchema: z.object({
        text: z.string()
      })
    },
    async ({ text }) => ({
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            echo: text,
            configuredProtocol: protocol,
            processId: process.pid
          })
        }
      ]
    })
  );

  server.registerTool(
    'get-protocol-info',
    {
      description: 'Return this process protocol version and PID.'
    },
    async () => ({
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            configuredProtocol: protocol,
            processId: process.pid
          })
        }
      ]
    })
  );

  return server;
}

const handler = createMcpHandler(
  createProtocolPinnedServer,
  {
    legacy:
      protocol === '2026-07-28'
        ? 'reject'
        : 'stateless'
  }
);

const nodeHandler = toNodeHandler(handler);
const validateHost = localhostHostValidation();
const validateOrigin = localhostOriginValidation();

const httpServer = createServer((req, res) => {
  const requestUrl = new URL(
    req.url ?? '/',
    `http://${req.headers.host ?? `${host}:${port}`}`
  );

  if (requestUrl.pathname === '/health') {
    res.statusCode = 200;
    res.setHeader('content-type', 'application/json');
    res.end(
      JSON.stringify({
        status: 'UP',
        configuredProtocol: protocol,
        processId: process.pid
      })
    );
    return;
  }

  if (requestUrl.pathname !== '/mcp') {
    res.statusCode = 404;
    res.end('Not Found');
    return;
  }

  if (
    !validateHost(req, res) ||
    !validateOrigin(req, res)
  ) {
    return;
  }

  void nodeHandler(req, res);
});

httpServer.listen(port, host, () => {
  console.error(
    `[mcp-server] pid=${process.pid} protocol=${protocol} endpoint=http://${host}:${port}/mcp`
  );
});

async function shutdown(signal: string): Promise<void> {
  console.error(`[mcp-server] ${signal}, shutting down`);
  await handler.close();

  httpServer.close(() => {
    process.exit(0);
  });
}

process.on('SIGINT', () => {
  void shutdown('SIGINT');
});

process.on('SIGTERM', () => {
  void shutdown('SIGTERM');
});
