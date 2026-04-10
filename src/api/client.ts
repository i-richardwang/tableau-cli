import { RestApiCredentials } from './methods/authenticatedMethods.js';
import {
  AuthenticatedAuthenticationMethods,
  AuthenticationMethods,
} from './methods/authenticationMethods.js';
import ContentExplorationMethods from './methods/contentExplorationMethods.js';
import DatasourcesMethods from './methods/datasourcesMethods.js';
import MetadataMethods from './methods/metadataMethods.js';
import ViewsMethods from './methods/viewsMethods.js';
import VizqlDataServiceMethods from './methods/vizqlDataServiceMethods.js';
import WorkbooksMethods from './methods/workbooksMethods.js';

const API_VERSION = '3.24';
const TIMEOUT_MS = 120_000;

export class RestApi {
  private _host: string;
  private _creds?: RestApiCredentials;

  constructor(host: string) {
    this._host = host.replace(/\/$/, '');
  }

  private get baseUrl(): string {
    return `${this._host}/api/${API_VERSION}`;
  }

  private get baseUrlWithoutVersion(): string {
    return `${this._host}/api/-`;
  }

  private get creds(): RestApiCredentials {
    if (!this._creds) {
      throw new Error('Not authenticated. Call signIn() first.');
    }
    return this._creds;
  }

  get siteId(): string {
    return this.creds.site.id;
  }

  get userId(): string {
    return this.creds.user.id;
  }

  async signIn(config: { siteName: string; patName: string; patValue: string }): Promise<void> {
    const methods = new AuthenticationMethods(this.baseUrl, { timeout: TIMEOUT_MS });
    this._creds = await methods.signIn(config);
  }

  async signOut(): Promise<void> {
    if (!this._creds) return;
    const methods = new AuthenticatedAuthenticationMethods(this.baseUrl, this._creds, {
      timeout: TIMEOUT_MS,
    });
    await methods.signOut();
    this._creds = undefined;
  }

  get datasources(): DatasourcesMethods {
    return new DatasourcesMethods(this.baseUrl, this.creds, { timeout: TIMEOUT_MS });
  }

  get views(): ViewsMethods {
    return new ViewsMethods(this.baseUrl, this.creds, { timeout: TIMEOUT_MS });
  }

  get workbooks(): WorkbooksMethods {
    return new WorkbooksMethods(this.baseUrl, this.creds, { timeout: TIMEOUT_MS });
  }

  get contentExploration(): ContentExplorationMethods {
    return new ContentExplorationMethods(this.baseUrlWithoutVersion, this.creds, {
      timeout: TIMEOUT_MS,
    });
  }

  get vizqlDataService(): VizqlDataServiceMethods {
    const baseUrl = `${this._host}/api/v1/vizql-data-service`;
    return new VizqlDataServiceMethods(baseUrl, this.creds, { timeout: TIMEOUT_MS });
  }

  get metadata(): MetadataMethods {
    const baseUrl = `${this._host}/api/metadata`;
    return new MetadataMethods(baseUrl, this.creds, { timeout: TIMEOUT_MS });
  }
}
