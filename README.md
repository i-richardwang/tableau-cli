# tableau-cli

A command-line interface for Tableau Server / Tableau Cloud, designed for AI agent integration. All output is structured JSON to stdout, with agent-friendly error messages that include actionable hints.

## Why CLI over MCP?

MCP (Model Context Protocol) servers continuously occupy agent context. A CLI tool follows a simpler call-execute-exit pattern — the agent invokes a command, reads the JSON output, and moves on. This project provides the same capabilities as the [tableau-mcp](https://github.com/anthropics/tableau-mcp) server with behavioral alignment in data transformations, error handling, and output structures.

## Quick Start

### Prerequisites

- Node.js >= 22.7.5
- A Tableau Server or Tableau Cloud instance
- A [Personal Access Token (PAT)](https://help.tableau.com/current/server/en-us/security_personal_access_tokens.htm)

### Install

```bash
git clone <repo-url>
cd tableau-cli
npm install
npm run build
npm link   # makes `tableau-cli` available globally
```

### Configure

```bash
# Option 1: CLI config (saved to ~/.tableau-cli.json)
tableau-cli config set \
  --server https://your-tableau-server.com \
  --site-name YourSite \
  --pat-name your-token-name \
  --pat-value your-token-value

# Option 2: Environment variables
export SERVER=https://your-tableau-server.com
export SITE_NAME=YourSite
export PAT_NAME=your-token-name
export PAT_VALUE=your-token-value
```

Environment variables take precedence over the config file. `siteName` defaults to `""` (the default site) if not set.

```bash
# Verify configuration
tableau-cli config show
```

## Commands

### Search

Search across all content types (workbooks, views, datasources, etc.).

```bash
tableau-cli search "Superstore"
tableau-cli search "Sales" --type workbook,view
tableau-cli search "Revenue" --limit 10 --order-by hitsTotal:desc
```

### Datasources

```bash
# List all datasources
tableau-cli datasources list
tableau-cli ds list --filter "name:has:Sales" --limit 50

# Get field metadata (VizQL Data Service + Metadata API enrichment)
tableau-cli datasources metadata <luid>

# Query datasource data (VizQL Data Service)
tableau-cli datasources query <luid> --query '{"fields": [{"fieldCaption": "Category"}, {"fieldCaption": "Sales"}]}'
tableau-cli ds query <luid> --query '{"fields": [...]}' --limit 100
```

### Views

```bash
# List views
tableau-cli views list
tableau-cli views list --filter "name:has:Dashboard" --format table

# Get view data as CSV
tableau-cli views data <viewId>

# Download view image
tableau-cli views image <viewId> -o dashboard.png
tableau-cli views image <viewId> --width 1200 --height 800 --img-format SVG -o dashboard.svg
```

### Workbooks

```bash
# List workbooks
tableau-cli workbooks list
tableau-cli wb list --filter "name:eq:Finance" --format table

# Get workbook details (includes views with usage statistics)
tableau-cli workbooks get <workbookId>
```

### Config

```bash
tableau-cli config set --server https://tableau.example.com
tableau-cli config show
```

## Output

All commands output structured JSON to stdout by default. Use `--format table` for human-readable table output.

```bash
# JSON (default, for agent consumption)
tableau-cli ds list

# Table (for human reading)
tableau-cli ds list --format table
```

### Error Output

Errors are also structured JSON, designed to guide agents toward resolution:

```json
{
  "isError": true,
  "errorType": "feature-disabled",
  "message": "The VizQL Data Service is disabled on this Tableau Server.",
  "hint": "To enable it, use TSM using the instructions at https://help.tableau.com/..."
}
```

Error types include: `authentication-error`, `feature-disabled`, `tableau-api-error`, `config-error`, `validation-error`, and translated [VDS error codes](https://help.tableau.com/current/api/vizql-data-service/en-us/docs/vds_error_codes.html) with actionable hints.

## API Coverage

| Area | APIs Used |
|------|-----------|
| Authentication | REST API v3.24 — PAT sign-in / sign-out |
| Datasources | REST API (list) + VizQL Data Service (metadata, query) + Metadata API (GraphQL enrichment) |
| Views | REST API (list, data, image) |
| Workbooks | REST API (list, get with view enrichment) |
| Search | Content Exploration API |

## Development

```bash
# Run without building (via tsx)
npm run dev -- views list

# Type-check
npm run lint

# Build
npm run build
```

## Acknowledgements

This project is derived from [@tableau/mcp-server](https://github.com/tableau/tableau-mcp), adapting its Tableau REST API, VizQL Data Service, and Metadata API integrations into a CLI format.

## License

[Apache License 2.0](./LICENSE)
