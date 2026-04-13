# tableau-cli

A command-line interface for Tableau Server / Tableau Cloud, designed for AI agent integration. All output is structured JSON to stdout, with agent-friendly error messages that include actionable hints.

## Why CLI over MCP?

MCP (Model Context Protocol) servers continuously occupy agent context — every tool description is loaded into the system prompt, even when only one command is needed. A CLI follows a simpler call-execute-exit pattern: the agent invokes a command, reads the JSON output, and moves on.

The companion Claude Code skill under `skills/` extends the same idea to command knowledge — the full reference is loaded only when the agent is about to execute a command, not kept in context upfront. See [Use with Claude Code](#use-with-claude-code) below.

This project provides the same capabilities as the [tableau-mcp](https://github.com/tableau/tableau-mcp) server, with behavioral alignment in data transformations, error handling, and output structures.

## Quick Start

### Prerequisites

- Python >= 3.10
- A Tableau Server or Tableau Cloud instance
- A [Personal Access Token (PAT)](https://help.tableau.com/current/server/en-us/security_personal_access_tokens.htm)

### Install

```bash
git clone https://github.com/i-richardwang/tableau-cli.git
cd tableau-cli
pip install -e .

# Optional: install conversion dependencies (TDSX/HYPER → Parquet/CSV)
pip install -e ".[convert]"
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

## Use with Claude Code

This repository ships with a Claude Code skill under `skills/`. Once loaded, it gives an agent enough context to route a user's request to the right command — without putting the full CLI reference into the system prompt.

```
skills/
├── SKILL.md              # Intent routing + environment check
└── references/
    ├── cli.md            # Full command reference (loaded before executing)
    └── installation.md   # Install + auth setup (loaded if not configured)
```

Once Claude Code has loaded the skill, a typical interaction looks like:

1. The agent runs `tableau-cli --help` to verify the CLI is installed and configured. If not, it loads `references/installation.md` and stops until setup is complete.
2. The agent maps the user's intent to a subcommand using the Intent Routing table in `SKILL.md` (e.g., "find datasources with Sales in the name" → `ds list --filter "name:has:Sales"`).
3. Before constructing the actual command, the agent loads `references/cli.md` — the skill explicitly forbids guessing flags from memory, so the reference is the source of truth for syntax.
4. The agent runs the command and parses the structured JSON output, including the `hint` field on errors.

Common multi-step workflows (e.g., `ds download → convert → load with Polars/Pandas`) are pre-defined under Intent Routing in `SKILL.md`, so the agent doesn't have to reason about chaining from scratch.

You can of course use `tableau-cli` directly from a shell without the skill — the skill is only needed when you want an agent to drive the tool.

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

# Download datasource file (.tdsx)
tableau-cli datasources download <datasourceId> -o ./data/

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

### Convert

Convert Tableau TDSX/HYPER files to Parquet or CSV. Requires `pip install tableau-cli[convert]`.

```bash
# Convert TDSX to Parquet (default)
tableau-cli convert data.tdsx
tableau-cli convert data.tdsx -o ./output/

# Convert to CSV
tableau-cli convert data.tdsx --to csv
tableau-cli convert data.tdsx --to csv -o ./output/

# Convert standalone HYPER file
tableau-cli convert extract.hyper --to csv -o ./output/result.csv
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

### File Output

Commands that save files (`ds download`, `views image -o`, `convert`) output a JSON object with the file path to stdout, enabling agents to chain operations:

```bash
# Download and convert pipeline
tableau-cli ds download <id> -o ./data/        # → {"filePath": ".../data.tdsx"}
tableau-cli convert ./data/data.tdsx -o ./data/ # → {"filePath": ".../data.parquet"}
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
| Datasources | REST API (list, download) + VizQL Data Service (metadata, query) + Metadata API (GraphQL enrichment) |
| Views | REST API (list, data, image) |
| Workbooks | REST API (list, get with view enrichment) |
| Search | Content Exploration API |
| Convert | Local file conversion: TDSX/HYPER → Parquet/CSV (optional dependencies) |

## Development

```bash
# Run directly
python -m tableau_cli.cli views list

# Install in editable mode
pip install -e .
```

## Acknowledgements

This project is derived from [@tableau/mcp-server](https://github.com/tableau/tableau-mcp), adapting its Tableau REST API, VizQL Data Service, and Metadata API integrations into a CLI format.

## License

[Apache License 2.0](./LICENSE)
