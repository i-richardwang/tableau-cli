import { Command } from 'commander';

import { withAuth } from '../auth/withAuth.js';
import { resolveConfig } from '../config/store.js';
import { output } from '../output/format.js';

export function registerDatasourcesCommand(program: Command): void {
  const ds = program.command('datasources').alias('ds').description('Manage data sources');

  ds.command('list')
    .description('List published data sources')
    .option('--filter <filter>', 'Filter string (e.g., name:eq:Superstore)')
    .option('--limit <n>', 'Max results', '100')
    .option('--format <fmt>', 'Output format: json | table', 'json')
    .action(async (opts) => {
      const config = resolveConfig();
      const result = await withAuth(config, async (api) => {
        return api.datasources.listDatasources({
          siteId: api.siteId,
          filter: opts.filter,
          pageSize: parseInt(opts.limit),
        });
      });
      const rows = result.datasources.map((ds) => ({
        id: ds.id,
        name: ds.name,
        project: ds.project?.name ?? '',
        description: ds.description ?? '',
      }));
      output(rows, opts.format);
    });

  ds.command('metadata <luid>')
    .description('Get data source field metadata')
    .option('--format <fmt>', 'Output format: json | table', 'json')
    .action(async (luid: string, opts) => {
      const config = resolveConfig();
      const result = await withAuth(config, async (api) => {
        return api.vizqlDataService.readMetadata({
          datasource: { datasourceLuid: luid },
        });
      });
      output(result.data ?? [], opts.format);
    });

  ds.command('query <luid>')
    .description('Query a data source using VizQL Data Service')
    .requiredOption('--query <json>', 'Query JSON (fields, filters, etc.)')
    .option('--limit <n>', 'Row limit')
    .option('--format <fmt>', 'Output format: json | table', 'json')
    .action(async (luid: string, opts) => {
      const config = resolveConfig();
      const query = JSON.parse(opts.query);
      const result = await withAuth(config, async (api) => {
        return api.vizqlDataService.queryDatasource({
          datasource: { datasourceLuid: luid },
          query,
          options: {
            returnFormat: 'OBJECTS',
            rowLimit: opts.limit ? parseInt(opts.limit) : undefined,
          },
        });
      });
      output(result.data ?? [], opts.format);
    });
}
