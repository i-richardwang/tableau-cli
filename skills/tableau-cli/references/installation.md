---
name: tableau-cli-installation
description: Installation and authentication setup for tableau-cli. Load when the CLI is not installed or not configured.
---

## Installation

```bash
pip install "tableau-cli[convert]"
```

Without `[convert]`, only core features are available (search, datasources, views, workbooks) — the `convert` command and `ds download --to parquet/csv` will not work.

## Upgrade

```bash
pip install --upgrade "tableau-cli[convert]"
```

## Authentication

tableau-cli uses Personal Access Token (PAT) authentication.

### Option 1: CLI config (saved to ~/.tableau-cli.json)

```bash
tableau-cli config set \
  --server https://your-tableau-server.com \
  --site-name YourSite \
  --pat-name your-token-name \
  --pat-value your-token-value
```

### Option 2: Environment variables

```bash
export SERVER=https://your-tableau-server.com
export SITE_NAME=YourSite
export PAT_NAME=your-token-name
export PAT_VALUE=your-token-value
```

Environment variables take precedence over the config file. `SITE_NAME` defaults to `""` (the default site) if not set.

## Verification

```bash
tableau-cli config show
tableau-cli ds list --limit 1
```

`config show` displays the current configuration (PAT value is masked). If `ds list` returns data, authentication is working.
