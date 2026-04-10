import { Command } from 'commander';

import { withAuth } from '../auth/withAuth.js';
import { resolveConfig } from '../config/store.js';
import { output } from '../output/format.js';

export function registerWorkbooksCommand(program: Command): void {
  const wb = program.command('workbooks').alias('wb').description('Manage workbooks');

  wb.command('list')
    .description('List workbooks on the site')
    .option('--filter <filter>', 'Filter string (e.g., name:eq:Finance)')
    .option('--limit <n>', 'Max results', '100')
    .option('--format <fmt>', 'Output format: json | table', 'json')
    .action(async (opts) => {
      const config = resolveConfig();
      const result = await withAuth(config, async (api) => {
        return api.workbooks.queryWorkbooksForSite({
          siteId: api.siteId,
          filter: opts.filter,
          pageSize: parseInt(opts.limit),
        });
      });
      const rows = result.workbooks.map((wb) => ({
        id: wb.id,
        name: wb.name,
        project: wb.project?.name ?? '',
        description: wb.description ?? '',
      }));
      output(rows, opts.format);
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
        const views = await api.views.queryViewsForWorkbook({
          workbookId,
          siteId: api.siteId,
        });
        return { ...workbook, views: { view: views } };
      });
      output(result, opts.format);
    });
}
