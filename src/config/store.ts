import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { Config, PartialConfig } from './types.js';

const CONFIG_PATH = join(homedir(), '.tableau-cli.json');

export function loadFileConfig(): PartialConfig {
  try {
    const raw = readFileSync(CONFIG_PATH, 'utf-8');
    return JSON.parse(raw) as PartialConfig;
  } catch {
    return {};
  }
}

export function saveFileConfig(config: PartialConfig): void {
  mkdirSync(dirname(CONFIG_PATH), { recursive: true });
  writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2) + '\n', 'utf-8');
}

export function resolveConfig(): Config {
  const file = loadFileConfig();

  const server = process.env.SERVER || file.server;
  const siteName = process.env.SITE_NAME || file.siteName || '';
  const patName = process.env.PAT_NAME || file.patName;
  const patValue = process.env.PAT_VALUE || file.patValue;

  if (!server) {
    throw new Error('Missing required config: server. Set via `tableau-cli config set --server <url>` or SERVER env var.');
  }
  if (!patName || !patValue) {
    throw new Error('Missing required config: patName/patValue. Set via `tableau-cli config set --pat-name <name> --pat-value <value>` or PAT_NAME/PAT_VALUE env vars.');
  }

  return { server, siteName, patName, patValue };
}
