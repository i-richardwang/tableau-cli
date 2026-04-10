import { Command } from 'commander';

import { isAxiosError } from './utils/axios.js';

import { registerConfigCommand } from './commands/config.js';
import { registerDatasourcesCommand } from './commands/datasources.js';
import { registerSearchCommand } from './commands/search.js';
import { registerViewsCommand } from './commands/views.js';
import { registerWorkbooksCommand } from './commands/workbooks.js';
import { CliError, CliErrorOutput } from './errors/cliError.js';

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
  const output = toErrorOutput(err);
  // Structured JSON to stdout so agents can parse it
  process.stdout.write(JSON.stringify(output, null, 2) + '\n');
  process.exit(1);
});

function toErrorOutput(err: unknown): CliErrorOutput {
  // Our own structured errors
  if (err instanceof CliError) {
    return err.toOutput();
  }

  // Axios HTTP errors (from Tableau REST API)
  if (isAxiosError(err)) {
    const status = err.response?.status;
    const data = err.response?.data;

    // Tableau REST API error format: { error: { summary, detail, code } }
    if (data?.error) {
      const { summary, detail, code } = data.error;
      return {
        isError: true,
        errorType: 'tableau-api-error',
        message: detail ? `${summary}: ${detail}` : summary ?? err.message,
        details: code ? `Tableau error code: ${code}` : undefined,
      };
    }

    return {
      isError: true,
      errorType: 'http-error',
      message: `HTTP ${status}: ${err.message}`,
      details: typeof data === 'string' ? data : undefined,
    };
  }

  // Config validation errors
  if (err instanceof Error && err.message.startsWith('Missing required config:')) {
    return {
      isError: true,
      errorType: 'config-error',
      message: err.message,
      hint: 'Run `tableau-cli config set` to configure, or set environment variables.',
    };
  }

  // JSON parse errors (bad --query input)
  if (err instanceof SyntaxError) {
    return {
      isError: true,
      errorType: 'invalid-input',
      message: err.message,
      hint: 'Check that your --query argument is valid JSON.',
    };
  }

  // Fallback
  const message = err instanceof Error ? err.message : String(err);
  return {
    isError: true,
    errorType: 'unknown-error',
    message,
  };
}
