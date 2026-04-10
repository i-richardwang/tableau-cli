import { Command } from 'commander';

import { registerConfigCommand } from './commands/config.js';
import { registerDatasourcesCommand } from './commands/datasources.js';
import { registerSearchCommand } from './commands/search.js';
import { registerViewsCommand } from './commands/views.js';
import { registerWorkbooksCommand } from './commands/workbooks.js';

const program = new Command();

program
  .name('tableau-cli')
  .description('CLI tool for interacting with Tableau Server/Cloud')
  .version('0.1.0');

registerConfigCommand(program);
registerDatasourcesCommand(program);
registerViewsCommand(program);
registerWorkbooksCommand(program);
registerSearchCommand(program);

program.parseAsync(process.argv).catch((err) => {
  console.error(err.message ?? err);
  process.exit(1);
});
