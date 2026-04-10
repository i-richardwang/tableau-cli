import { Zodios } from '@zodios/core';

import { CliError, FeatureDisabledError } from '../../errors/cliError.js';
import { isAxiosError } from '../../utils/axios.js';
import { viewsApis } from '../apis/viewsApi.js';
import { Pagination } from '../types/pagination.js';
import { View } from '../types/view.js';
import AuthenticatedMethods, { RestApiCredentials } from './authenticatedMethods.js';

export default class ViewsMethods extends AuthenticatedMethods<typeof viewsApis> {
  constructor(baseUrl: string, creds: RestApiCredentials, options?: { timeout?: number }) {
    super(new Zodios(baseUrl, viewsApis, { axiosConfig: options }), creds);
  }

  getView = async (args: { viewId: string; siteId: string }): Promise<View> => {
    return (
      await this._apiClient.getView({
        params: { siteId: args.siteId, viewId: args.viewId },
        ...this.authHeader,
      })
    ).view;
  };

  queryViewData = async (args: { viewId: string; siteId: string }): Promise<string> => {
    return await this._apiClient.queryViewData({
      params: { siteId: args.siteId, viewId: args.viewId },
      ...this.authHeader,
    });
  };

  queryViewImage = async (args: {
    viewId: string;
    siteId: string;
    width?: number;
    height?: number;
    format?: 'PNG' | 'SVG';
  }): Promise<string> => {
    try {
      return await this._apiClient.queryViewImage({
        params: { siteId: args.siteId, viewId: args.viewId },
        queries: { vizWidth: args.width, vizHeight: args.height, resolution: 'high', format: args.format },
        ...this.authHeader,
        responseType: 'arraybuffer',
      });
    } catch (error) {
      if (isAxiosError(error) && error.response?.data) {
        let errorData = error.response.data;
        // When responseType is 'arraybuffer', parse the response body
        if (!errorData.error) {
          try {
            const text = new TextDecoder().decode(errorData);
            errorData = JSON.parse(text);
          } catch {
            throw error;
          }
        }
        if (errorData.error?.code === '403157') {
          const isSvg = args.format === 'SVG';
          throw new FeatureDisabledError(
            isSvg
              ? 'SVG format is not supported on this Tableau Server. It requires Tableau 2026.2.0 or later.'
              : 'The image format feature is disabled on this Tableau Server.',
            isSvg ? 'Retry with --img-format PNG instead.' : undefined,
          );
        }
        if (errorData.error) {
          const { summary, detail } = errorData.error;
          throw new CliError({
            errorType: 'view-image-error',
            message: detail ? `${summary}: ${detail}` : summary,
          });
        }
      }
      throw error;
    }
  };

  queryViewsForSite = async (args: {
    siteId: string;
    filter?: string;
    pageSize?: number;
    pageNumber?: number;
  }): Promise<{ pagination: Pagination; views: View[] }> => {
    const response = await this._apiClient.queryViewsForSite({
      params: { siteId: args.siteId },
      queries: {
        includeUsageStatistics: true,
        filter: args.filter,
        pageSize: args.pageSize,
        pageNumber: args.pageNumber,
      },
      ...this.authHeader,
    });
    return {
      pagination: response.pagination,
      views: response.views.view ?? [],
    };
  };

  queryViewsForWorkbook = async (args: {
    workbookId: string;
    siteId: string;
  }): Promise<View[]> => {
    return (
      await this._apiClient.queryViewsForWorkbook({
        params: { siteId: args.siteId, workbookId: args.workbookId },
        queries: { includeUsageStatistics: true },
        ...this.authHeader,
      })
    ).views.view;
  };
}
