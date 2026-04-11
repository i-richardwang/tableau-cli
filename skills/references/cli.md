---
name: tableau-cli-reference
description: Full CLI command reference for tableau-cli. Load before running any command as the authoritative source for flags and syntax.
---

# CLI Command Reference

All commands output JSON (indent=2) by default. List commands support `--format table` for human-readable output.

Errors are also structured JSON:
```json
{
  "isError": true,
  "errorType": "<type>",
  "message": "<description>",
  "hint": "<suggested action>"
}
```

---

## search

Search across all content types on the site.

```bash
tableau-cli search "keyword"
tableau-cli search "keyword" --type workbook,view,datasource
tableau-cli search "keyword" --limit 10 --order-by hitsTotal:desc
tableau-cli search --format table
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `terms` | string (positional) | none | Search terms, optional |
| `--type` | string | none | Comma-separated content types (workbook, view, datasource, etc.) |
| `--limit` | int | 100 | Max results to return |
| `--order-by` | string | none | Sort method (e.g., `hitsTotal:desc`) |
| `--format` | json / table | json | Output format |

View results include `parentWorkbookName` (parent workbook) and `totalViewCount` (total views).

---

## datasources (alias: ds)

### ds list

```bash
tableau-cli ds list
tableau-cli ds list --filter "name:has:keyword" --limit 50 --format table
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--filter` | string | none | Server-side filter (see filter syntax below) |
| `--page-size` | int | none | Items per page |
| `--limit` | int | none | Max total results |
| `--format` | json / table | json | Output format |

Automatically paginates until all results are fetched or limit is reached.

### ds download

```bash
tableau-cli ds download <datasource-id> -o ./output/
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `datasource_id` | string (positional) | required | Datasource LUID |
| `-o, --output` | path | `.` | Output path (directory or filename) |

Output: `{"filePath": "<absolute path>"}`

### ds metadata

View datasource field metadata. Requires VizQL Data Service.

```bash
tableau-cli ds metadata <luid>
tableau-cli ds metadata <luid> --format table
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `luid` | string (positional) | required | Datasource LUID |
| `--format` | json / table | json | Output format |

Returns:
- `datasourceDescription` — datasource description
- `fieldGroups[].fields[]` — field list (name, dataType, role, formula, description, etc.)
- `parameters[]` — parameter list (name, parameterType, dataType, value, etc.)

Attempts to enrich via GraphQL Metadata API; falls back to base VizQL metadata if unavailable.

### ds query

Query datasource data directly. Requires VizQL Data Service.

```bash
tableau-cli ds query <luid> --query '{"fields": [{"fieldCaption": "Category"}, {"fieldCaption": "Sales"}]}'
tableau-cli ds query <luid> --query '{"fields": [...]}' --limit 100 --format table
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `luid` | string (positional) | required | Datasource LUID |
| `--query` | JSON string | required | Query definition (fields, filters, etc.) |
| `--limit` | int | none | Row limit (client-side truncation) |
| `--format` | json / table | json | Output format |

`--query` must be valid JSON; otherwise reports `invalid-input` error. `--limit` truncates client-side, not server-side.

---

## views

Views include worksheets (Sheets), dashboards, and stories.

### views list

```bash
tableau-cli views list
tableau-cli views list --filter "name:has:keyword" --format table
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--filter` | string | none | Server-side filter |
| `--page-size` | int | none | Items per page |
| `--limit` | int | none | Max total results |
| `--format` | json / table | json | Output format |

Results include `workbookId` to trace back to the parent workbook.

### views data

Export view data as CSV.

```bash
tableau-cli views data <view-id>
```

| Option | Type | Description |
|--------|------|-------------|
| `view_id` | string (positional) | View LUID |

Output: CSV text written directly to stdout (not JSON).

### views image

Export view as image.

```bash
tableau-cli views image <view-id> -o output.png
tableau-cli views image <view-id> --width 1200 --height 800 -o output.png
tableau-cli views image <view-id> --img-format SVG -o output.svg
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `view_id` | string (positional) | required | View LUID |
| `--width` | int | none | Image width in pixels |
| `--height` | int | none | Image height in pixels |
| `--img-format` | PNG / SVG | PNG | Image format |
| `-o, --output` | path | none | Output file path |

With `-o`: outputs `{"filePath": "<absolute path>"}`. Without `-o`: base64-encoded image to stdout.

---

## workbooks (alias: wb)

### wb list

```bash
tableau-cli wb list
tableau-cli wb list --filter "name:has:keyword" --format table
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--filter` | string | none | Server-side filter |
| `--page-size` | int | none | Items per page |
| `--limit` | int | none | Max total results |
| `--format` | json / table | json | Output format |

### wb get

View workbook details, including all views with usage statistics.

```bash
tableau-cli wb get <workbook-id>
tableau-cli wb get <workbook-id> --format table
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `workbook_id` | string (positional) | required | Workbook LUID |
| `--format` | json / table | json | Output format |

---

## convert

Local file conversion: TDSX/HYPER → Parquet/CSV. Requires `tableau-cli[convert]`.

```bash
tableau-cli convert data.tdsx
tableau-cli convert data.tdsx -o ./output/
tableau-cli convert data.tdsx --to csv -o ./output/
tableau-cli convert extract.hyper -o ./output/result.parquet
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `input_path` | path (positional) | required | Input file (.tdsx or .hyper) |
| `--to` | parquet / csv | parquet | Output format |
| `-o, --output` | path | none | Output path (directory or filename); defaults to input file directory |

Output: `{"filePath": "<absolute path>"}`

Reports `missing-dependencies` error if convert extras are not installed, with hint to run `pip install "tableau-cli[convert]"`.

---

## config

### config show

```bash
tableau-cli config show
```

Outputs current configuration as JSON. PAT value is masked as `"****"`.

### config set

```bash
tableau-cli config set --server https://... --site-name ... --pat-name ... --pat-value ...
```

All options are optional; only updates the specified fields. Saves to `~/.tableau-cli.json`.

---

## Filter Syntax

The `--filter` option uses `field:operator:value` format:

| Operator | Meaning | Example |
|----------|---------|---------|
| `eq` | Exact match | `name:eq:Superstore` |
| `has` | Contains | `name:has:Sales` |
| `in` | Multi-value match | `name:in:[A,B,C]` |

---

## Intent → Command Quick Reference

| User wants to… | Command |
|-----------------|---------|
| Search content (any type) | `search "keyword"` |
| Find datasources | `ds list --filter "name:has:..."` |
| Download a datasource file | `ds download <id> -o dir/` |
| Inspect datasource fields | `ds metadata <luid>` |
| Query data from a datasource | `ds query <luid> --query '{...}'` |
| Find a dashboard/view | `views list --filter "name:has:..."` |
| Export view data | `views data <view-id>` |
| Export view screenshot | `views image <view-id> -o file.png` |
| Find workbooks | `wb list --filter "name:has:..."` |
| See views in a workbook | `wb get <workbook-id>` |
| Convert TDSX to Parquet | `convert file.tdsx -o dir/` |
| Download and convert for analysis | `ds download` → `convert` |
