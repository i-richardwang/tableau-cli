---
name: tableau-cli
description: "Interact with Tableau Server / Cloud via the tableau-cli command: search content, query datasources, download files, export view images and data, convert TDSX/HYPER to Parquet/CSV. Use when the user wants to find, download, query, or export any Tableau content."
---

# Tableau CLI

Interact with Tableau Server / Cloud via the `tableau-cli` command.

## References

Load these files when needed — do not load all of them upfront:

- [references/cli.md](references/cli.md) — full CLI command reference. Load before running any `tableau-cli` command or looking up flags and syntax.
- [references/installation.md](references/installation.md) — installation and authentication setup. Load if `tableau-cli` is not installed or not configured.

## Environment Check

Before running any command, verify the CLI is available:

```bash
tableau-cli --help
```

If `tableau-cli` is not installed or the API key is missing, load [references/installation.md](references/installation.md) and stop until setup is complete.

## CLI Reference

Before running any `tableau-cli` command, load [references/cli.md](references/cli.md) as the source of truth for exact flags, subcommands, and examples. Do not guess command syntax from memory.

## Intent Routing

The following requests can be handled directly with CLI commands. Load [references/cli.md](references/cli.md) and execute:

- Search content across types — `search`
- List/filter datasources, views, workbooks, or projects — `ds list` / `views list` / `wb list` / `projects list`
- Download a datasource file — `ds download` (supports `--to parquet` / `--to csv` for direct conversion)
- Inspect datasource field metadata and table relationships — `ds metadata`
- Query data from a datasource — `ds query`
- View details of a single view, incl. its web URL and upstream datasources — `views get`
- Export view data as CSV — `views data` (supports `--vf "Field=Value"` view filters)
- Export view as image — `views image` (supports `--vf "Field=Value"` view filters)
- View workbook details, its views, and its web URL — `wb get`
- Convert TDSX/HYPER to Parquet/CSV — `convert`

Common combined workflows:

**Download datasource for local analysis**: `ds list` → `ds download --to parquet` → load with Polars/Pandas

**Quick data extraction (no file download)**: `ds metadata` → `ds query` (requires VizQL Data Service; fall back to download + convert if unavailable)

**Export dashboard screenshot**: `views list` → `views image`

**From dashboard to data**: `search` or `views get` → `upstreamDatasources[].luid` → `ds metadata` → `ds query`
