function formatValue(value: unknown): string {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    if (value.length === 0) return '';
    // Handle tags: [{label: "x"}, ...]
    if (value[0] && typeof value[0] === 'object' && 'label' in value[0]) {
      return value.map((v: { label: string }) => v.label).join(', ');
    }
    return value.map(formatValue).join(', ');
  }
  if (typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    // Handle tags object: {tag: [{label: "x"}, ...]} or {tag: undefined}
    if ('tag' in obj) {
      return Array.isArray(obj.tag) ? obj.tag.map((t: { label: string }) => t.label).join(', ') : '';
    }
    // Handle empty-like objects
    const values = Object.values(obj).filter((v) => v != null);
    if (values.length === 0) return '';
    // Handle common nested objects: {name: "x", id: "y"} → show name or id
    if ('name' in obj && obj.name) return String(obj.name);
    if ('id' in obj && obj.id) return String(obj.id);
    return JSON.stringify(obj);
  }
  return String(value);
}

export function outputTable(rows: Record<string, unknown>[]): void {
  if (rows.length === 0) {
    process.stdout.write('(no results)\n');
    return;
  }

  // Flatten: for each column, if value is an object with a single scalar key, inline it
  const columns = Object.keys(rows[0]);
  const formatted = rows.map((row) => {
    const out: Record<string, string> = {};
    for (const col of columns) {
      out[col] = formatValue(row[col]);
    }
    return out;
  });

  const widths = columns.map((col) =>
    Math.max(col.length, ...formatted.map((row) => row[col].length)),
  );

  const header = columns.map((col, i) => col.toUpperCase().padEnd(widths[i])).join('  ');
  const separator = widths.map((w) => '-'.repeat(w)).join('  ');

  process.stdout.write(header + '\n');
  process.stdout.write(separator + '\n');

  for (const row of formatted) {
    const line = columns.map((col, i) => row[col].padEnd(widths[i])).join('  ');
    process.stdout.write(line + '\n');
  }
}
