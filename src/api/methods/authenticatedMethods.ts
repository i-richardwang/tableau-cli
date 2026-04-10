import { ZodiosEndpointDefinitions, ZodiosInstance } from '@zodios/core';

import Methods from './methods.js';

export type RestApiCredentials = {
  site: { id: string };
  user: { id: string };
  token: string;
};

type AuthHeaders = {
  headers: { 'X-Tableau-Auth': string };
};

export default abstract class AuthenticatedMethods<
  T extends ZodiosEndpointDefinitions,
> extends Methods<T> {
  private _creds: RestApiCredentials;

  protected get authHeader(): AuthHeaders {
    return {
      headers: { 'X-Tableau-Auth': this._creds.token },
    };
  }

  protected get siteId(): string {
    return this._creds.site.id;
  }

  protected get userId(): string {
    return this._creds.user.id;
  }

  constructor(apiClient: ZodiosInstance<T>, creds: RestApiCredentials) {
    super(apiClient);
    this._creds = creds;
  }
}
