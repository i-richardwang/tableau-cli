import { Command } from 'commander';

import { withAuth } from '../auth/withAuth.js';
import { resolveConfig } from '../config/store.js';
import { output } from '../output/format.js';
import { paginate } from '../utils/paginate.js';

export function registerWorkbooksCommand(program: Command): void {
  const wb = program.command('workbooks').alias('wb').description('Manage workbooks');

  wb.command('list')
    .description('List workbooks on the site')
    .option('--filter <filter>', 'Filter string (e.g., name:eq:Finance)')
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
            const { pagination, workbooks: data } = await api.workbooks.queryWorkbooksForSite({
              siteId: api.siteId,
              filter: opts.filter ?? '',
              pageSize: pageConfig.pageSize,
              pageNumber: pageConfig.pageNumber,
            });
            return { pagination, data };
          },
        });
      });
      output(result, opts.format);
    });

  wb.command('get <workbookId>')
    .description('Get workbook details')
    .option('--format <fmt>', 'Output format: json | table', 'json')
    .action(async (workbookId: string, opts) => {
      const config = resolveConfig();
      const result = await withAuth(config, async (api) => {
        const workbook = await api.workbooks.getWorkbook({
          workbookId,
          siteId: api.siteId,
        });

        // Enrich views with usage statistics (consistent with MCP behavior)
        if (workbook.views) {
          const views = await api.views.queryViewsForWorkbook({
            workbookId,
            siteId: api.siteId,
          });
          workbook.views.view = views;
        }

        return workbook;
      });
      output(result, opts.format);
    });
}
