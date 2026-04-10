export interface Config {
  server: string;
  siteName: string;
  patName: string;
  patValue: string;
}

export type PartialConfig = Partial<Config>;
