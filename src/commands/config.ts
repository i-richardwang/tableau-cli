import { Command } from 'commander';

import { loadFileConfig, saveFileConfig } from '../config/store.js';

export function registerConfigCommand(program: Command): void {
  const configCmd = program.command('config').description('Manage CLI configuration');

  configCmd
    .command('set')
    .description('Set configuration values')
    .option('--server <url>', 'Tableau server URL')
    .option('--site-name <name>', 'Tableau site name')
    .option('--pat-name <name>', 'Personal Access Token name')
    .option('--pat-value <value>', 'Personal Access Token value')
    .action((opts) => {
      const existing = loadFileConfig();
      if (opts.server) existing.server = opts.server;
      if (opts.siteName) existing.siteName = opts.siteName;
      if (opts.patName) existing.patName = opts.patName;
      if (opts.patValue) existing.patValue = opts.patValue;
      saveFileConfig(existing);
      console.error('Configuration saved.');
    });

  configCmd
    .command('show')
    .description('Show current configuration')
    .action(() => {
      const config = loadFileConfig();
      const display = {
        ...config,
        patValue: config.patValue ? '****' : undefined,
      };
      console.log(JSON.stringify(display, null, 2));
    });
}
