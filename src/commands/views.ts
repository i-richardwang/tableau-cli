import { Command } from 'commander';
import { writeFileSync } from 'node:fs';

import { withAuth } from '../auth/withAuth.js';
import { resolveConfig } from '../config/store.js';
import { output } from '../output/format.js';

export function registerViewsCommand(program: Command): void {
  const views = program.command('views').description('Manage views');

  views
    .command('list')
    .description('List views on the site')
    .option('--filter <filter>', 'Filter string (e.g., name:has:Sales)')
    .option('--limit <n>', 'Max results', '100')
    .option('--format <fmt>', 'Output format: json | table', 'json')
    .action(async (opts) => {
      const config = resolveConfig();
      const result = await withAuth(config, async (api) => {
        return api.views.queryViewsForSite({
          siteId: api.siteId,
          filter: opts.filter,
          pageSize: parseInt(opts.limit),
        });
      });
      const rows = result.views.map((v) => ({
        id: v.id,
        name: v.name,
        createdAt: v.createdAt,
        updatedAt: v.updatedAt,
        viewCount: v.usage?.totalViewCount ?? 0,
      }));
      output(rows, opts.format);
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
    .option('--format <fmt>', 'Image format: PNG | SVG', 'PNG')
    .option('-o, --output <path>', 'Output file path')
    .action(async (viewId: string, opts) => {
      const config = resolveConfig();
      const imageData = await withAuth(config, async (api) => {
        return api.views.queryViewImage({
          viewId,
          siteId: api.siteId,
          width: opts.width ? parseInt(opts.width) : undefined,
          height: opts.height ? parseInt(opts.height) : undefined,
          format: opts.format as 'PNG' | 'SVG',
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
