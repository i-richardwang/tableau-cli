import { Config } from '../config/types.js';
import { RestApi } from '../api/client.js';

export async function withAuth<T>(
  config: Config,
  fn: (api: RestApi) => Promise<T>,
): Promise<T> {
  const api = new RestApi(config.server);
  await api.signIn({
    siteName: config.siteName,
    patName: config.patName,
    patValue: config.patValue,
  });
  try {
    return await fn(api);
  } finally {
    await api.signOut().catch(() => {});
  }
}
