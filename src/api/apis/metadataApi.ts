import { makeApi, makeEndpoint, ZodiosEndpointDefinitions } from '@zodios/core';
import { z } from 'zod';

export const graphqlResponse = z.object({
  data: z.object({
    publishedDatasources: z.array(
      z.object({
        name: z.string().nullable(),
        description: z.string().nullable(),
        owner: z.object({ name: z.string().nullable() }),
        fields: z.array(
          z.object({
            name: z.string(),
            isHidden: z.boolean().nullable(),
            description: z.string().nullable(),
            fullyQualifiedName: z.string(),
            __typename: z.string(),
            dataCategory: z.string().nullish(),
            role: z.string().nullish(),
            dataType: z.string().nullish(),
            defaultFormat: z.string().nullish(),
            semanticRole: z.string().nullish(),
            aggregation: z.string().nullish(),
            formula: z.string().nullish(),
          }),
        ),
      }),
    ),
  }),
});

export type GraphQLResponse = z.infer<typeof graphqlResponse>;

const graphqlEndpoint = makeEndpoint({
  method: 'post',
  path: '/graphql',
  alias: 'graphql',
  response: graphqlResponse,
  parameters: [{ name: 'query', type: 'Body', schema: z.object({ query: z.string() }) }],
});

const metadataApi = makeApi([graphqlEndpoint]);
export const metadataApis = [...metadataApi] as const satisfies ZodiosEndpointDefinitions;
