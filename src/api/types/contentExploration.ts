import { z } from 'zod';

const searchContentItemSchema = z.object({
  uri: z.string(),
  content: z.record(z.string(), z.unknown()),
});

export const searchContentResponseSchema = z
  .object({
    next: z.string(),
    prev: z.string(),
    pageIndex: z.number().int(),
    startIndex: z.number().int(),
    total: z.number().int(),
    limit: z.number().int(),
    items: z.array(searchContentItemSchema),
  })
  .partial();

export type SearchContentItem = z.infer<typeof searchContentItemSchema>;
export type SearchContentResponse = z.infer<typeof searchContentResponseSchema>;
