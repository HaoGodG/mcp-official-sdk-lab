import { Client, StreamableHTTPClientTransport } from '@modelcontextprotocol/client';

type ProtocolVersion =
  | '2025-03-26'
  | '2025-06-18'
  | '2025-11-25'
  | '2026-07-28';

type Action = 'list' | 'call';

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

const url =
  readArg('--url') ??
  process.env.MCP_SERVER_URL ??
  'http://127.0.0.1:3100/mcp';

const action = (readArg('--action') ?? 'list') as Action;
const toolName = readArg('--tool') ?? 'echo';
const toolArgsText = readArg('--args') ?? '{"text":"hello-mcp"}';

if (action !== 'list' && action !== 'call') {
  throw new Error('Unsupported --action. Use list or call.');
}

const clientOptions =
  protocol === '2026-07-28'
    ? {
        versionNegotiation: {
          mode: { pin: '2026-07-28' as const }
        },
        supportedProtocolVersions: [protocol]
      }
    : {
        versionNegotiation: {
          mode: 'legacy' as const
        },
        supportedProtocolVersions: [protocol]
      };

const client = new Client(
  {
    name: 'mcp-official-sdk-test-client',
    version: '1.0.0'
  },
  clientOptions
);

try {
  await client.connect(
    new StreamableHTTPClientTransport(new URL(url))
  );

  console.log(
    JSON.stringify(
      {
        connected: true,
        target: url,
        requestedProtocol: protocol,
        negotiatedProtocol: client.getNegotiatedProtocolVersion(),
        protocolEra: client.getProtocolEra(),
        serverInfo: client.getServerVersion()
      },
      null,
      2
    )
  );

  if (action === 'list') {
    const result = await client.listTools();
    console.log(JSON.stringify(result, null, 2));
  } else {
    let args: Record<string, unknown>;

    try {
      args = JSON.parse(toolArgsText) as Record<string, unknown>;
    } catch {
      throw new Error(`--args must be valid JSON: ${toolArgsText}`);
    }

    const result = await client.callTool({
      name: toolName,
      arguments: args
    });

    console.log(JSON.stringify(result, null, 2));
  }
} finally {
  await client.close();
}
