import { Zodios } from '@zodios/core';

import { workbooksApis } from '../apis/workbooksApi.js';
import { Pagination } from '../types/pagination.js';
import { Workbook } from '../types/workbook.js';
import AuthenticatedMethods, { RestApiCredentials } from './authenticatedMethods.js';

export default class WorkbooksMethods extends AuthenticatedMethods<typeof workbooksApis> {
  constructor(baseUrl: string, creds: RestApiCredentials, options?: { timeout?: number }) {
    super(new Zodios(baseUrl, workbooksApis, { axiosConfig: options }), creds);
  }

  getWorkbook = async (args: { workbookId: string; siteId: string }): Promise<Workbook> => {
    return (
      await this._apiClient.getWorkbook({
        params: { siteId: args.siteId, workbookId: args.workbookId },
        ...this.authHeader,
      })
    ).workbook;
  };

  queryWorkbooksForSite = async (args: {
    siteId: string;
    filter?: string;
    pageSize?: number;
    pageNumber?: number;
  }): Promise<{ pagination: Pagination; workbooks: Workbook[] }> => {
    const response = await this._apiClient.queryWorkbooksForSite({
      params: { siteId: args.siteId },
      queries: { filter: args.filter, pageSize: args.pageSize, pageNumber: args.pageNumber },
      ...this.authHeader,
    });
    return {
      pagination: response.pagination,
      workbooks: response.workbooks.workbook ?? [],
    };
  };
}
