import { makeApi, makeEndpoint, ZodiosEndpointDefinitions } from '@zodios/core';
import { z } from 'zod';

export const functionSchema = z.enum([
  'SUM', 'AVG', 'MEDIAN', 'COUNT', 'COUNTD', 'MIN', 'MAX', 'STDEV', 'VAR', 'COLLECT',
  'YEAR', 'QUARTER', 'MONTH', 'WEEK', 'DAY',
  'TRUNC_YEAR', 'TRUNC_QUARTER', 'TRUNC_MONTH', 'TRUNC_WEEK', 'TRUNC_DAY',
  'AGG', 'NONE', 'UNSPECIFIED',
]);

const dataTypeSchema = z.enum([
  'INTEGER', 'REAL', 'STRING', 'DATETIME', 'BOOLEAN', 'DATE', 'SPATIAL', 'UNKNOWN',
]);

const fieldMetadataSchema = z
  .object({
    fieldName: z.string(),
    fieldCaption: z.string(),
    dataType: dataTypeSchema,
    defaultAggregation: functionSchema,
    columnClass: z.enum(['COLUMN', 'BIN', 'GROUP', 'CALCULATION', 'TABLE_CALCULATION']),
    formula: z.string(),
    logicalTableId: z.string(),
  })
  .partial()
  .passthrough();

const sortDirectionSchema = z.enum(['ASC', 'DESC']);

const fieldBaseSchema = z.object({
  fieldCaption: z.string(),
  fieldAlias: z.string().optional(),
  maxDecimalPlaces: z.number().int().gte(0).optional(),
  sortDirection: sortDirectionSchema.optional(),
  sortPriority: z.number().int().gt(0).optional(),
});

export const fieldSchema = z.union([
  fieldBaseSchema.strict(),
  fieldBaseSchema.extend({ function: functionSchema }).strict(),
  fieldBaseSchema.extend({ calculation: z.string() }).strict(),
  fieldBaseSchema.extend({ binSize: z.number().gt(0) }).strict(),
]);

const dimensionFilterFieldSchema = z.object({ fieldCaption: z.string() }).strict();
const measureFilterFieldSchema = z.object({ fieldCaption: z.string(), function: functionSchema }).strict();
const calculatedFilterFieldSchema = z.object({ calculation: z.string() }).strict();

export const filterFieldSchema = z.union([
  dimensionFilterFieldSchema,
  measureFilterFieldSchema,
  calculatedFilterFieldSchema,
]);

const filterBaseSchema = z.object({
  field: filterFieldSchema,
  context: z.boolean().optional(),
});

const periodTypeSchema = z.enum(['MINUTES', 'HOURS', 'DAYS', 'WEEKS', 'MONTHS', 'QUARTERS', 'YEARS']);

export const filterSchema = z.union([
  // SET filter
  filterBaseSchema.extend({
    filterType: z.literal('SET'),
    values: z.union([z.array(z.string()), z.array(z.number()), z.array(z.boolean())]),
    exclude: z.boolean().optional(),
  }).strict(),
  // TOP filter
  filterBaseSchema.extend({
    filterType: z.literal('TOP'),
    howMany: z.number().int(),
    fieldToMeasure: filterFieldSchema,
    direction: z.enum(['TOP', 'BOTTOM']).optional().default('TOP'),
  }).strict(),
  // MATCH filters
  z.object({ field: z.union([dimensionFilterFieldSchema, calculatedFilterFieldSchema]), context: z.boolean().optional(), filterType: z.literal('MATCH'), startsWith: z.string(), endsWith: z.string().optional(), contains: z.string().optional(), exclude: z.boolean().optional() }).strict(),
  z.object({ field: z.union([dimensionFilterFieldSchema, calculatedFilterFieldSchema]), context: z.boolean().optional(), filterType: z.literal('MATCH'), startsWith: z.string().optional(), endsWith: z.string(), contains: z.string().optional(), exclude: z.boolean().optional() }).strict(),
  z.object({ field: z.union([dimensionFilterFieldSchema, calculatedFilterFieldSchema]), context: z.boolean().optional(), filterType: z.literal('MATCH'), startsWith: z.string().optional(), endsWith: z.string().optional(), contains: z.string(), exclude: z.boolean().optional() }).strict(),
  // QUANTITATIVE_NUMERICAL
  filterBaseSchema.extend({ filterType: z.literal('QUANTITATIVE_NUMERICAL'), quantitativeFilterType: z.literal('RANGE'), min: z.number(), max: z.number(), includeNulls: z.boolean().optional() }).strict(),
  filterBaseSchema.extend({ filterType: z.literal('QUANTITATIVE_NUMERICAL'), quantitativeFilterType: z.literal('MIN'), min: z.number(), includeNulls: z.boolean().optional() }).strict(),
  filterBaseSchema.extend({ filterType: z.literal('QUANTITATIVE_NUMERICAL'), quantitativeFilterType: z.literal('MAX'), max: z.number(), includeNulls: z.boolean().optional() }).strict(),
  // QUANTITATIVE_DATE
  filterBaseSchema.extend({ filterType: z.literal('QUANTITATIVE_DATE'), quantitativeFilterType: z.literal('RANGE'), minDate: z.string(), maxDate: z.string(), includeNulls: z.boolean().optional() }).strict(),
  filterBaseSchema.extend({ filterType: z.literal('QUANTITATIVE_DATE'), quantitativeFilterType: z.literal('MIN'), minDate: z.string(), includeNulls: z.boolean().optional() }).strict(),
  filterBaseSchema.extend({ filterType: z.literal('QUANTITATIVE_DATE'), quantitativeFilterType: z.literal('MAX'), maxDate: z.string(), includeNulls: z.boolean().optional() }).strict(),
  // DATE (relative)
  filterBaseSchema.extend({ filterType: z.literal('DATE'), dateRangeType: z.literal('CURRENT'), periodType: periodTypeSchema, anchorDate: z.string().optional(), includeNulls: z.boolean().optional() }).strict(),
  filterBaseSchema.extend({ filterType: z.literal('DATE'), dateRangeType: z.literal('LAST'), periodType: periodTypeSchema, anchorDate: z.string().optional(), includeNulls: z.boolean().optional() }).strict(),
  filterBaseSchema.extend({ filterType: z.literal('DATE'), dateRangeType: z.literal('LASTN'), periodType: periodTypeSchema, rangeN: z.number().int(), anchorDate: z.string().optional(), includeNulls: z.boolean().optional() }).strict(),
]);

const queryParameterSchema = z.object({
  parameterCaption: z.string(),
  value: z.union([z.number(), z.string(), z.boolean(), z.null()]),
});

const datasourceSchema = z.object({
  datasourceLuid: z.string().nonempty(),
  connections: z.array(z.object({
    connectionLuid: z.string().optional(),
    connectionUsername: z.string(),
    connectionPassword: z.string(),
  })).optional(),
});

export const querySchema = z.strictObject({
  fields: z.array(fieldSchema),
  filters: z.array(filterSchema).optional(),
  parameters: z.array(queryParameterSchema).optional(),
});

export const queryRequestSchema = z.object({
  datasource: datasourceSchema,
  query: querySchema,
  options: z.object({
    returnFormat: z.enum(['OBJECTS', 'ARRAYS']).optional(),
    debug: z.boolean().default(false).optional(),
    disaggregate: z.boolean().optional(),
    rowLimit: z.number().int().min(1).optional(),
  }).optional(),
}).passthrough();

export const readMetadataRequestSchema = z.object({
  datasource: datasourceSchema,
  options: z.object({
    returnFormat: z.enum(['OBJECTS', 'ARRAYS']).optional(),
    debug: z.boolean().default(false).optional(),
  }).optional(),
}).passthrough();

const tableauErrorSchema = z.object({
  errorCode: z.string(),
  message: z.string(),
}).partial().passthrough();

export const metadataOutputSchema = z.object({
  data: z.array(fieldMetadataSchema),
}).partial().passthrough();

export const queryOutputSchema = z.object({
  data: z.array(z.unknown()),
}).partial().passthrough();

// Exported types
export type QueryRequest = z.infer<typeof queryRequestSchema>;
export type QueryOutput = z.infer<typeof queryOutputSchema>;
export type ReadMetadataRequest = z.infer<typeof readMetadataRequestSchema>;
export type MetadataResponse = z.infer<typeof metadataOutputSchema>;

// Endpoints
const queryDatasourceEndpoint = makeEndpoint({
  method: 'post',
  path: '/query-datasource',
  alias: 'queryDatasource',
  description: 'Queries a specific data source and returns the resulting data.',
  requestFormat: 'json',
  parameters: [{ name: 'body', type: 'Body', schema: queryRequestSchema }],
  response: queryOutputSchema,
  errors: [
    { status: 'default', schema: tableauErrorSchema },
    { status: 404, schema: z.any() },
  ],
});

const readMetadataEndpoint = makeEndpoint({
  method: 'post',
  path: '/read-metadata',
  alias: 'readMetadata',
  description: 'Requests metadata for a specific data source.',
  requestFormat: 'json',
  parameters: [{ name: 'body', type: 'Body', schema: readMetadataRequestSchema }],
  response: metadataOutputSchema,
  errors: [{ status: 404, schema: z.any() }],
});

const vizqlDataServiceApi = makeApi([queryDatasourceEndpoint, readMetadataEndpoint]);
export const vizqlDataServiceApis = [...vizqlDataServiceApi] as const satisfies ZodiosEndpointDefinitions;
