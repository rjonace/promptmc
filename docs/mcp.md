# MCP Server Configuration

PromptMC ships a [Model Context Protocol](https://modelcontextprotocol.io) server so MCP-capable AI assistants can drive [OpenMC](https://docs.openmc.org/en/stable/) workflows natively — validation, schema checks, plotting, execution, and result parsing from inside your chat client.

The server is installed with PromptMC (`pip install promptmc`) and started by the `promptmc-mcp` command, which speaks MCP over stdio. You normally don't run it by hand — the client launches it for you using the configuration below.

## Prerequisites

- `promptmc` installed and on `PATH` (verify with `promptmc-mcp --help`).
- For execution, geometry-debug checks, and plot rendering: OpenMC installed and `OPENMC_CROSS_SECTIONS` pointing at a `cross_sections.xml`. See [installation](installation.md). Planning and XML/schema validation work without it.

> **Tip:** If `promptmc-mcp` isn't on your client's `PATH` (common with GUI apps that don't inherit your shell environment), use the absolute path. Find it with `which promptmc-mcp`.

## Standard configuration

Most clients (Claude Desktop, Cursor, Google Antigravity) read a JSON object keyed by `mcpServers`. The PromptMC entry is the same everywhere — only the file location differs:

```json
{
  "mcpServers": {
    "promptmc": {
      "command": "promptmc-mcp",
      "env": {
        "OPENMC_CROSS_SECTIONS": "/path/to/cross_sections.xml"
      }
    }
  }
}
```

The `env` block is optional; omit it if you only need planning and validation. The only variable the server requires is `OPENMC_CROSS_SECTIONS`, and only for execution, geometry-debug checks, and plot rendering.

## Per-client setup

### Claude Desktop

Claude Desktop is available on **macOS and Windows only** — there is no official Linux build. On Linux, use **Claude Code** (below) or another MCP client.

1. Open **Settings → Developer → Edit Config** (this creates/opens `claude_desktop_config.json`).
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
2. Add the [standard configuration](#standard-configuration) above.
3. Restart Claude Desktop. PromptMC's tools appear under the MCP/tools (🔌) menu.

### Claude Code

Use the CLI to register the server (no manual JSON editing):

```bash
# Project scope (writes a .mcp.json in the repo, shareable with your team)
claude mcp add promptmc --scope project \
  --env OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml \
  -- promptmc-mcp

# Or user scope (available across all your projects)
claude mcp add promptmc --scope user -- promptmc-mcp
```

Verify with `claude mcp list`, or inspect the resulting `.mcp.json` — it uses the same `mcpServers` schema shown above.

### Cursor

1. Open **Settings → MCP → Add new global MCP server** (or create the file directly):
   - Global: `~/.cursor/mcp.json`
   - Per-project: `.cursor/mcp.json` in the workspace root
2. Add the [standard configuration](#standard-configuration).
3. Reload Cursor. The server shows up under **Settings → MCP** with a green status dot when connected.

### Google Antigravity

1. Open the MCP settings panel (**Settings → MCP Servers**, or the MCP entry in the Agent Manager).
2. Add a server using the [standard configuration](#standard-configuration) — Antigravity uses the same `mcpServers` JSON schema.
3. Reload the window so the agent picks up PromptMC's tools.

### VS Code (GitHub Copilot)

VS Code uses a `servers` key (not `mcpServers`) in `.vscode/mcp.json`:

```json
{
  "servers": {
    "promptmc": {
      "command": "promptmc-mcp",
      "env": {
        "OPENMC_CROSS_SECTIONS": "/path/to/cross_sections.xml"
      }
    }
  }
}
```

Place this at `.vscode/mcp.json` in your workspace (or add it to user settings via **MCP: Add Server**). Start it from the **Extensions / MCP** view, then use the tools from Copilot Chat in **Agent** mode.

### Other clients

Any MCP client that launches stdio servers works. Point it at the `promptmc-mcp` command with the `OPENMC_CROSS_SECTIONS` environment variable, following that client's own config format.

## Verify the connection

Once configured, ask your assistant to call `openmc_check_installation` and `openmc_check_cross_sections`, or `openmc_list_templates`. A successful response confirms the server is wired up. The available [tools](https://modelcontextprotocol.io/docs/concepts/tools) and [resources](https://modelcontextprotocol.io/docs/concepts/resources) are listed in the [README](../README.md#mcp-server).

For an end-to-end walkthrough, see the [MCP example](../examples/mcp/README.md).
