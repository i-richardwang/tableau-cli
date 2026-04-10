import { Command } from 'commander';

import { withAuth } from '../auth/withAuth.js';
import { resolveConfig } from '../config/store.js';
import { output } from '../output/format.js';

export function registerSearchCommand(program: Command): void {
  program
    .command('search [terms]')
    .description('Search across all content types')
    .option('--type <types>', 'Comma-separated content types (e.g., workbook,view,datasource)')
    .option('--limit <n>', 'Max results', '20')
    .option('--format <fmt>', 'Output format: json | table', 'json')
    .action(async (terms: string | undefined, opts) => {
      const config = resolveConfig();
      const filterParts: string[] = [];
      if (opts.type) {
        filterParts.push(`type:in:[${opts.type}]`);
      }
      const result = await withAuth(config, async (api) => {
        return api.contentExploration.searchContent({
          terms,
          limit: parseInt(opts.limit),
          filter: filterParts.length > 0 ? filterParts.join(',') : undefined,
        });
      });
      const items = result.items ?? [];
      const rows = items.map((item) => ({
        uri: item.uri,
        type: (item.content as Record<string, unknown>).type ?? '',
        name: (item.content as Record<string, unknown>).name ?? '',
      }));
      output(rows, opts.format);
    });
}
