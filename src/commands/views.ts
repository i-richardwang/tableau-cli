import { Command } from 'commander';
import { writeFileSync } from 'node:fs';

import { withAuth } from '../auth/withAuth.js';
import { resolveConfig } from '../config/store.js';
import { output } from '../output/format.js';
import { paginate } from '../utils/paginate.js';

export function registerViewsCommand(program: Command): void {
  const views = program.command('views').description('Manage views');

  views
    .command('list')
    .description('List views on the site')
    .option('--filter <filter>', 'Filter string (e.g., name:has:Sales)')
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
            const { pagination, views: data } = await api.views.queryViewsForSite({
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

  views
    .command('data <viewId>')
    .description('Get view data as CSV')
    .action(async (viewId: string) => {
      const config = resolveConfig();
      const csv = await withAuth(config, async (api) => {
        return api.views.queryViewData({ viewId, siteId: api.siteId });
      });
      process.stdout.write(csv);
    });

  views
    .command('image <viewId>')
    .description('Download view image')
    .option('--width <n>', 'Image width in pixels')
    .option('--height <n>', 'Image height in pixels')
    .option('--img-format <fmt>', 'Image format: PNG | SVG', 'PNG')
    .option('-o, --output <path>', 'Output file path')
    .action(async (viewId: string, opts) => {
      const config = resolveConfig();
      const imageData = await withAuth(config, async (api) => {
        return api.views.queryViewImage({
          viewId,
          siteId: api.siteId,
          width: opts.width ? parseInt(opts.width) : undefined,
          height: opts.height ? parseInt(opts.height) : undefined,
          format: opts.imgFormat as 'PNG' | 'SVG',
        });
      });
      if (opts.output) {
        const buffer = Buffer.from(imageData, 'base64');
        writeFileSync(opts.output, buffer);
        console.error(`Image saved to ${opts.output}`);
      } else {
        process.stdout.write(imageData);
      }
    });
}
