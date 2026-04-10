import { RestApi } from '../api/client.js';
import { Config } from '../config/types.js';
import { AuthenticationError } from '../errors/cliError.js';
import { isAxiosError } from '../utils/axios.js';

export async function withAuth<T>(
  config: Config,
  fn: (api: RestApi) => Promise<T>,
): Promise<T> {
  const api = new RestApi(config.server);
  try {
    await api.signIn({
      siteName: config.siteName,
      patName: config.patName,
      patValue: config.patValue,
    });
  } catch (error) {
    if (isAxiosError(error)) {
      const status = error.response?.status;
      if (status === 401 || status === 403) {
        throw new AuthenticationError(
          `Sign-in failed (HTTP ${status}). The PAT may be expired or invalid.`,
        );
      }
      if (!error.response) {
        throw new AuthenticationError(
          `Cannot connect to Tableau Server at ${config.server}: ${error.message}. Check the server URL.`,
        );
      }
    }
    throw error;
  }
  try {
    return await fn(api);
  } finally {
    await api.signOut().catch(() => {});
  }
}
