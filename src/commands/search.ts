import { Command } from 'commander';

import { withAuth } from '../auth/withAuth.js';
import { resolveConfig } from '../config/store.js';
import { output } from '../output/format.js';
import { reduceSearchContentResponse } from '../utils/searchContentUtils.js';

export function registerSearchCommand(program: Command): void {
  program
    .command('search [terms]')
    .description('Search across all content types')
    .option('--type <types>', 'Comma-separated content types (e.g., workbook,view,datasource)')
    .option('--limit <n>', 'Max results', '100')
    .option('--order-by <method>', 'Sort method (e.g., hitsTotal:desc)')
    .option('--format <fmt>', 'Output format: json | table', 'json')
    .action(async (terms: string | undefined, opts) => {
      const config = resolveConfig();
      const filterParts: string[] = [];
      if (opts.type) {
        const types = opts.type.split(',');
        if (types.length === 1) {
          filterParts.push(`type:eq:${types[0]}`);
        } else {
          filterParts.push(`type:in:[${types.join(',')}]`);
        }
      }
      const result = await withAuth(config, async (api) => {
        const response = await api.contentExploration.searchContent({
          terms,
          page: 0,
          limit: parseInt(opts.limit),
          order_by: opts.orderBy,
          filter: filterParts.length > 0 ? filterParts.join(',') : undefined,
        });
        return reduceSearchContentResponse(response);
      });
      output(result, opts.format);
    });
}
