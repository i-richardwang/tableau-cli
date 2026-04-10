import { Zodios } from '@zodios/core';

import { datasourcesApis } from '../apis/datasourcesApi.js';
import { DataSource } from '../types/dataSource.js';
import { Pagination } from '../types/pagination.js';
import AuthenticatedMethods, { RestApiCredentials } from './authenticatedMethods.js';

export default class DatasourcesMethods extends AuthenticatedMethods<typeof datasourcesApis> {
  constructor(baseUrl: string, creds: RestApiCredentials, options?: { timeout?: number }) {
    super(new Zodios(baseUrl, datasourcesApis, { axiosConfig: options }), creds);
  }

  listDatasources = async (args: {
    siteId: string;
    filter?: string;
    pageSize?: number;
    pageNumber?: number;
  }): Promise<{ pagination: Pagination; datasources: DataSource[] }> => {
    const response = await this._apiClient.listDatasources({
      params: { siteId: args.siteId },
      queries: { filter: args.filter, pageSize: args.pageSize, pageNumber: args.pageNumber },
      ...this.authHeader,
    });
    return {
      pagination: response.pagination,
      datasources: response.datasources.datasource ?? [],
    };
  };

  queryDatasource = async (args: {
    siteId: string;
    datasourceId: string;
  }): Promise<DataSource> => {
    return (
      await this._apiClient.queryDatasource({
        params: { siteId: args.siteId, datasourceId: args.datasourceId },
        ...this.authHeader,
      })
    ).datasource;
  };
}
