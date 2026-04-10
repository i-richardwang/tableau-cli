import { ZodiosEndpointParameter } from '@zodios/core';
import { z } from 'zod';

export const paginationParameters = [
  {
    name: 'pageSize',
    type: 'Query',
    schema: z.number().optional(),
  },
  {
    name: 'pageNumber',
    type: 'Query',
    schema: z.number().optional(),
  },
] as const satisfies Array<ZodiosEndpointParameter>;
