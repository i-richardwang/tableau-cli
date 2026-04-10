/**
 * Structured error for CLI output.
 * All errors are output as JSON to stdout so agents can parse them.
 */
export interface CliErrorOutput {
  isError: true;
  errorType: string;
  message: string;
  details?: string;
  hint?: string;
}

export class CliError extends Error {
  readonly errorType: string;
  readonly details?: string;
  readonly hint?: string;

  constructor(opts: { errorType: string; message: string; details?: string; hint?: string }) {
    super(opts.message);
    this.errorType = opts.errorType;
    this.details = opts.details;
    this.hint = opts.hint;
  }

  toOutput(): CliErrorOutput {
    const output: CliErrorOutput = {
      isError: true,
      errorType: this.errorType,
      message: this.message,
    };
    if (this.details) output.details = this.details;
    if (this.hint) output.hint = this.hint;
    return output;
  }
}

export class FeatureDisabledError extends CliError {
  constructor(message: string, hint?: string) {
    super({ errorType: 'feature-disabled', message, hint });
  }
}

export class AuthenticationError extends CliError {
  constructor(message: string) {
    super({
      errorType: 'authentication-error',
      message,
      hint: 'Check your PAT credentials with `tableau-cli config show`. Ensure the token has not expired.',
    });
  }
}
