import { Zodios } from '@zodios/core';

import {
  MetadataResponse,
  QueryOutput,
  QueryRequest,
  ReadMetadataRequest,
  vizqlDataServiceApis,
} from '../apis/vizqlDataServiceApi.js';
import AuthenticatedMethods, { RestApiCredentials } from './authenticatedMethods.js';

export default class VizqlDataServiceMethods extends AuthenticatedMethods<
  typeof vizqlDataServiceApis
> {
  constructor(baseUrl: string, creds: RestApiCredentials, options?: { timeout?: number }) {
    super(new Zodios(baseUrl, vizqlDataServiceApis, { axiosConfig: options }), creds);
  }

  queryDatasource = async (queryRequest: QueryRequest): Promise<QueryOutput> => {
    return await this._apiClient.queryDatasource(queryRequest, { ...this.authHeader });
  };

  readMetadata = async (request: ReadMetadataRequest): Promise<MetadataResponse> => {
    return await this._apiClient.readMetadata(request, { ...this.authHeader });
  };
}
