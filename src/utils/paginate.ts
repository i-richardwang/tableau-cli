import { Pagination } from '../api/types/pagination.js';

export interface PageConfig {
  pageSize?: number;
  pageNumber?: number;
  limit?: number;
}

interface PaginateArgs<T> {
  pageConfig: PageConfig;
  getDataFn: (pagination: PageConfig) => Promise<{ pagination: Pagination; data: Array<T> }>;
}

export async function paginate<T>({ pageConfig, getDataFn }: PaginateArgs<T>): Promise<Array<T>> {
  const { pageSize, limit } = pageConfig;
  const { pagination, data } = await getDataFn(pageConfig);
  const result = [...data];

  let { totalAvailable, pageNumber } = pagination;
  while (totalAvailable > result.length && (!limit || limit > result.length)) {
    const { pagination: nextPagination, data: nextData } = await getDataFn({
      pageSize,
      pageNumber: pageNumber + 1,
      limit,
    });

    if (nextData.length === 0) {
      break;
    }

    ({ totalAvailable, pageNumber } = nextPagination);
    result.push(...nextData);
  }

  if (limit && limit < result.length) {
    result.length = limit;
  }

  return result;
}
