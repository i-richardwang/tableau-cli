import { outputJson } from './json.js';
import { outputTable } from './table.js';

export function output(data: unknown, format: string): void {
  if (format === 'table' && Array.isArray(data)) {
    outputTable(data as Record<string, unknown>[]);
  } else {
    outputJson(data);
  }
}
