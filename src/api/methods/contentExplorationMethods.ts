import { Zodios } from '@zodios/core';

import { contentExplorationApis } from '../apis/contentExplorationApi.js';
import { SearchContentResponse } from '../types/contentExploration.js';
import AuthenticatedMethods, { RestApiCredentials } from './authenticatedMethods.js';

export default class ContentExplorationMethods extends AuthenticatedMethods<
  typeof contentExplorationApis
> {
  constructor(baseUrl: string, creds: RestApiCredentials, options?: { timeout?: number }) {
    super(new Zodios(baseUrl, contentExplorationApis, { axiosConfig: options }), creds);
  }

  searchContent = async (queries: {
    terms?: string;
    page?: number;
    limit?: number;
    order_by?: string;
    filter?: string;
  }): Promise<SearchContentResponse> => {
    const cleanQueries = Object.fromEntries(
      Object.entries(queries).filter(([, v]) => v !== undefined),
    );
    const response = await this._apiClient.searchContent({
      queries: cleanQueries,
      ...this.authHeader,
    });
    return response.hits;
  };
}
