import { Zodios } from '@zodios/core';

import { GraphQLResponse, metadataApis } from '../apis/metadataApi.js';
import AuthenticatedMethods, { RestApiCredentials } from './authenticatedMethods.js';

export default class MetadataMethods extends AuthenticatedMethods<typeof metadataApis> {
  constructor(baseUrl: string, creds: RestApiCredentials, options?: { timeout?: number }) {
    super(new Zodios(baseUrl, metadataApis, { axiosConfig: options }), creds);
  }

  graphql = async (query: string): Promise<GraphQLResponse> => {
    return await this._apiClient.graphql({ query }, { ...this.authHeader });
  };
}
