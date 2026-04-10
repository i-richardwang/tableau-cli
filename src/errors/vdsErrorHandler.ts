import { CliError } from './cliError.js';

/**
 * Translates Tableau VizQL Data Service error codes into agent-friendly messages.
 * Based on: https://help.tableau.com/current/api/vizql-data-service/en-us/docs/vds_error_codes.html
 */
export function handleVdsError(
  errorMessage: string,
  httpStatus: number,
  tableauErrorCode: string | undefined,
): CliError {
  let condition: string | undefined;
  let details: string | undefined;
  let hint: string | undefined;

  switch (tableauErrorCode) {
    case '400000':
      condition = 'Bad request';
      details = 'The content of the request body is invalid. Check for missing or incomplete JSON.';
      hint = 'Verify the --query JSON is valid and complete.';
      break;
    case '400800':
      condition = 'Invalid formula for calculation';
      details = 'Invalid custom calculation syntax.';
      hint = 'See https://help.tableau.com/current/pro/desktop/en-us/functions_operators.htm';
      break;
    case '400802':
      condition = 'Invalid API request';
      details = "The incoming request isn't valid per the OpenAPI specification.";
      break;
    case '400803':
      condition = 'Validation failed';
      details = "The incoming request isn't valid per the validation rules.";
      hint = 'Check that all field names and filter values match the datasource metadata. Use `tableau-cli datasources metadata <luid>` to verify available fields.';
      break;
    case '400804':
      condition = 'Response too large';
      details = 'The response value exceeds the limit.';
      hint = 'You must apply a filter in your query to reduce the response size, or use --limit to restrict row count.';
      break;
    case '401001':
      condition = 'Login error';
      details = 'The login failed for the given user.';
      hint = 'Check your PAT credentials with `tableau-cli config show`.';
      break;
    case '401002':
      condition = 'Invalid authorization credentials';
      details = 'The provided auth token is formatted incorrectly.';
      hint = 'Re-authenticate by updating your PAT with `tableau-cli config set --pat-name <name> --pat-value <value>`.';
      break;
    case '403157':
      condition = 'Feature disabled';
      details = 'The VizQL Data Service feature is disabled on this server.';
      hint = 'Ask your Tableau Server admin to enable it via TSM. See https://help.tableau.com/current/server-linux/en-us/cli_configuration-set_tsm.htm';
      break;
    case '403800':
      condition = 'API access permission denied';
      details = "The user doesn't have API Access granted on the given data source.";
      hint = 'Set the API Access capability for this data source to Allowed. See https://help.tableau.com/current/online/en-us/permissions_capabilities.htm';
      break;
    case '404934':
      condition = 'Unknown field';
      details = "The requested field doesn't exist in this datasource.";
      hint = 'Use `tableau-cli datasources metadata <luid>` to see available fields and their exact names.';
      break;
    case '404950':
      condition = 'API endpoint not found';
      details = "The VizQL Data Service endpoint doesn't exist on this server.";
      hint = 'This feature may not be available on your Tableau Server version.';
      break;
    case '408000':
      condition = 'Request timeout';
      details = 'The query timed out.';
      hint = 'Try adding filters to reduce the data volume, or increase the scope of your query.';
      break;
    case '429000':
      condition = 'Too many requests';
      details = 'Rate limit exceeded.';
      hint = 'Wait before retrying. See https://help.tableau.com/current/api/vizql-data-service/en-us/docs/vds_limitations.html';
      break;
    case '409000':
      condition = 'User already on site';
      details = 'HTTP status conflict.';
      break;
    case '500000':
      condition = 'Internal server error';
      details = 'The request could not be completed.';
      break;
    case '500810':
      condition = 'Empty table response';
      details = 'The underlying data engine returned empty data.';
      hint = 'The datasource may have no data, or your filters may be too restrictive.';
      break;
    case '500811':
      condition = 'Missing table metadata';
      details = 'The underlying data engine returned empty metadata.';
      break;
    case '500812':
      condition = 'Error while processing an error';
      details = 'Internal processing error.';
      break;
    case '501000':
      condition = 'Not implemented';
      details = "Can't find response from upstream server.";
      break;
    case '503800':
      condition = 'VDS unavailable';
      details = 'The underlying data engine is unavailable.';
      hint = 'The server may be under maintenance. Try again later.';
      break;
    case '503801':
      condition = 'VDS discovery error';
      details = "The upstream service can't be found.";
      hint = 'The server may be under maintenance. Try again later.';
      break;
    case '504000':
      condition = 'Gateway timeout';
      details = 'The upstream service response timed out.';
      hint = 'Try a simpler query with fewer fields or more restrictive filters.';
      break;
  }

  return new CliError({
    errorType: condition ?? 'tableau-error',
    message: condition ? `${condition}: ${errorMessage}` : errorMessage,
    details,
    hint,
  });
}
