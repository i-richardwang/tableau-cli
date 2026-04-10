import { Command } from 'commander';

import { withAuth } from '../auth/withAuth.js';
import { resolveConfig } from '../config/store.js';
import { output } from '../output/format.js';
import { paginate } from '../utils/paginate.js';

export function registerDatasourcesCommand(program: Command): void {
  const ds = program.command('datasources').alias('ds').description('Manage data sources');

  ds.command('list')
    .description('List published data sources')
    .option('--filter <filter>', 'Filter string (e.g., name:eq:Superstore)')
    .option('--page-size <n>', 'Page size for API requests')
    .option('--limit <n>', 'Max total results')
    .option('--format <fmt>', 'Output format: json | table', 'json')
    .action(async (opts) => {
      const config = resolveConfig();
      const pageSize = opts.pageSize ? parseInt(opts.pageSize) : undefined;
      const limit = opts.limit ? parseInt(opts.limit) : undefined;
      const result = await withAuth(config, async (api) => {
        return paginate({
          pageConfig: { pageSize, limit },
          getDataFn: async (pageConfig) => {
            const { pagination, datasources: data } = await api.datasources.listDatasources({
              siteId: api.siteId,
              filter: opts.filter,
              pageSize: pageConfig.pageSize,
              pageNumber: pageConfig.pageNumber,
            });
            return { pagination, data };
          },
        });
      });
      output(result, opts.format);
    });

  ds.command('metadata <luid>')
    .description('Get data source field metadata')
    .option('--format <fmt>', 'Output format: json | table', 'json')
    .action(async (luid: string, opts) => {
      const config = resolveConfig();
      const result = await withAuth(config, async (api) => {
        // Fetch metadata from VizQL Data Service API
        const readMetadataResult = await api.vizqlDataService.readMetadata({
          datasource: { datasourceLuid: luid },
        });

        // Try to enrich with Metadata API (GraphQL)
        const { simplifyReadMetadataResult, combineFields, getGraphqlQuery } = await import(
          '../utils/datasourceMetadataUtils.js'
        );

        let graphqlResult;
        try {
          graphqlResult = await api.metadata.graphql(getGraphqlQuery(luid));
        } catch {
          // Metadata API may not be available
          return simplifyReadMetadataResult(readMetadataResult);
        }

        return combineFields(readMetadataResult, graphqlResult);
      });
      output(result, opts.format);
    });

  ds.command('query <luid>')
    .description('Query a data source using VizQL Data Service')
    .requiredOption('--query <json>', 'Query JSON (fields, filters, etc.)')
    .option('--limit <n>', 'Row limit')
    .option('--format <fmt>', 'Output format: json | table', 'json')
    .action(async (luid: string, opts) => {
      const config = resolveConfig();
      const query = JSON.parse(opts.query);
      const rowLimit = opts.limit ? parseInt(opts.limit) : undefined;
      const result = await withAuth(config, async (api) => {
        const queryResult = await api.vizqlDataService.queryDatasource({
          datasource: { datasourceLuid: luid },
          query,
          options: {
            returnFormat: 'OBJECTS',
            debug: true,
            disaggregate: false,
            rowLimit,
          },
        });

        // Truncate if needed (consistent with MCP behavior)
        if (rowLimit && queryResult.data && queryResult.data.length > rowLimit) {
          queryResult.data.length = rowLimit;
        }

        return queryResult;
      });
      output(result, opts.format);
    });
}
