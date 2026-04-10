export function outputTable(rows: Record<string, unknown>[]): void {
  if (rows.length === 0) {
    process.stdout.write('(no results)\n');
    return;
  }

  const columns = Object.keys(rows[0]);
  const widths = columns.map((col) =>
    Math.max(col.length, ...rows.map((row) => String(row[col] ?? '').length)),
  );

  const header = columns.map((col, i) => col.toUpperCase().padEnd(widths[i])).join('  ');
  const separator = widths.map((w) => '-'.repeat(w)).join('  ');

  process.stdout.write(header + '\n');
  process.stdout.write(separator + '\n');

  for (const row of rows) {
    const line = columns.map((col, i) => String(row[col] ?? '').padEnd(widths[i])).join('  ');
    process.stdout.write(line + '\n');
  }
}
