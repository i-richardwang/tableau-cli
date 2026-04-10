import { makeApi, makeEndpoint, ZodiosEndpointDefinitions } from '@zodios/core';
import { z } from 'zod';

import { paginationSchema } from '../types/pagination.js';
import { viewSchema } from '../types/view.js';
import { paginationParameters } from './paginationParameters.js';

const getViewEndpoint = makeEndpoint({
  method: 'get',
  path: '/sites/:siteId/views/:viewId',
  alias: 'getView',
  description: 'Gets the details of a specific view.',
  response: z.object({ view: viewSchema }),
});

const queryViewDataEndpoint = makeEndpoint({
  method: 'get',
  path: '/sites/:siteId/views/:viewId/data',
  alias: 'queryViewData',
  description: 'Returns a specified view rendered as CSV.',
  response: z.string(),
});

const queryViewImageEndpoint = makeEndpoint({
  method: 'get',
  path: '/sites/:siteId/views/:viewId/image',
  alias: 'queryViewImage',
  description: 'Returns an image of the specified view.',
  parameters: [
    { name: 'vizWidth', type: 'Query', schema: z.number().optional() },
    { name: 'vizHeight', type: 'Query', schema: z.number().optional() },
    { name: 'resolution', type: 'Query', schema: z.literal('high').optional() },
    { name: 'format', type: 'Query', schema: z.enum(['PNG', 'SVG']).optional() },
  ],
  response: z.string(),
});

const queryViewsForWorkbookEndpoint = makeEndpoint({
  method: 'get',
  path: '/sites/:siteId/workbooks/:workbookId/views',
  alias: 'queryViewsForWorkbook',
  description: 'Returns all the views for the specified workbook.',
  parameters: [
    { name: 'includeUsageStatistics', type: 'Query', schema: z.boolean().optional() },
  ],
  response: z.object({ views: z.object({ view: z.array(viewSchema) }) }),
});

const queryViewsForSiteEndpoint = makeEndpoint({
  method: 'get',
  path: '/sites/:siteId/views',
  alias: 'queryViewsForSite',
  description: 'Returns all the views for the specified site.',
  parameters: [
    ...paginationParameters,
    { name: 'includeUsageStatistics', type: 'Query', schema: z.boolean().optional() },
    { name: 'filter', type: 'Query', schema: z.string().optional() },
  ],
  response: z.object({
    pagination: paginationSchema,
    views: z.object({ view: z.array(viewSchema).optional() }),
  }),
});

const viewsApi = makeApi([
  getViewEndpoint,
  queryViewDataEndpoint,
  queryViewImageEndpoint,
  queryViewsForWorkbookEndpoint,
  queryViewsForSiteEndpoint,
]);

export const viewsApis = [...viewsApi] as const satisfies ZodiosEndpointDefinitions;
