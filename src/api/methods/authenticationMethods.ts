import { Zodios } from '@zodios/core';

import { authenticationApis } from '../apis/authenticationApi.js';
import { Credentials } from '../types/credentials.js';
import AuthenticatedMethods, { RestApiCredentials } from './authenticatedMethods.js';
import Methods from './methods.js';

export class AuthenticationMethods extends Methods<typeof authenticationApis> {
  constructor(baseUrl: string, options?: { timeout?: number }) {
    super(new Zodios(baseUrl, authenticationApis, { axiosConfig: options }));
  }

  signIn = async (config: {
    siteName: string;
    patName: string;
    patValue: string;
  }): Promise<Credentials> => {
    return (
      await this._apiClient.signIn({
        credentials: {
          site: { contentUrl: config.siteName },
          personalAccessTokenName: config.patName,
          personalAccessTokenSecret: config.patValue,
        },
      })
    ).credentials;
  };
}

export class AuthenticatedAuthenticationMethods extends AuthenticatedMethods<
  typeof authenticationApis
> {
  constructor(baseUrl: string, creds: RestApiCredentials, options?: { timeout?: number }) {
    super(new Zodios(baseUrl, authenticationApis, { axiosConfig: options }), creds);
  }

  signOut = async (): Promise<void> => {
    await this._apiClient.signOut(undefined, { ...this.authHeader });
  };
}
