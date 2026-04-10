import { isErrorFromAlias, Zodios } from '@zodios/core';

import { CliError, FeatureDisabledError } from '../../errors/cliError.js';
import { handleVdsError } from '../../errors/vdsErrorHandler.js';
import {
  MetadataResponse,
  QueryOutput,
  QueryRequest,
  ReadMetadataRequest,
  vizqlDataServiceApis,
} from '../apis/vizqlDataServiceApi.js';
import AuthenticatedMethods, { RestApiCredentials } from './authenticatedMethods.js';

const VDS_DISABLED_MESSAGE =
  'The VizQL Data Service is disabled on this Tableau Server. ' +
  'To enable it, use TSM using the instructions at https://help.tableau.com/current/server-linux/en-us/cli_configuration-set_tsm.htm#featuresvizqldataservicedeploywithtsm.';

export default class VizqlDataServiceMethods extends AuthenticatedMethods<
  typeof vizqlDataServiceApis
> {
  constructor(baseUrl: string, creds: RestApiCredentials, options?: { timeout?: number }) {
    super(new Zodios(baseUrl, vizqlDataServiceApis, { axiosConfig: options }), creds);
  }

  queryDatasource = async (queryRequest: QueryRequest): Promise<QueryOutput> => {
    try {
      return await this._apiClient.queryDatasource(queryRequest, { ...this.authHeader });
    } catch (error) {
      if (isErrorFromAlias(this._apiClient.api, 'queryDatasource', error)) {
        if (error.response.status === 404) {
          throw new FeatureDisabledError(VDS_DISABLED_MESSAGE);
        }
        const data = error.response.data as Record<string, string | undefined>;
        throw handleVdsError(
          data.message ?? 'Unknown Tableau error',
          error.response.status,
          data.errorCode ?? data['tab-error-code'],
        );
      }
      throw error;
    }
  };

  readMetadata = async (request: ReadMetadataRequest): Promise<MetadataResponse> => {
    try {
      return await this._apiClient.readMetadata(request, { ...this.authHeader });
    } catch (error) {
      if (
        isErrorFromAlias(this._apiClient.api, 'readMetadata', error) &&
        error.response.status === 404
      ) {
        throw new FeatureDisabledError(VDS_DISABLED_MESSAGE);
      }
      throw error;
    }
  };
}
