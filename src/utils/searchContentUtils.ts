import { SearchContentResponse } from '../api/types/contentExploration.js';

export type ReducedSearchContentResponse = Partial<Record<SearchItemContent, unknown>>;

type SearchItemContent =
  | 'caption'
  | 'comments'
  | 'connectedWorkbooksCount'
  | 'connectionType'
  | 'containerName'
  | 'datasourceIsPublished'
  | 'datasourceLuid'
  | 'downstreamWorkbookCount'
  | 'extractCreationPending'
  | 'extractRefreshedAt'
  | 'extractUpdatedAt'
  | 'favoritesTotal'
  | 'hasActiveDataQualityWarning'
  | 'hasExtracts'
  | 'hasSevereDataQualityWarning'
  | 'hitsSmallSpanTotal'
  | 'hitsTotal'
  | 'isCertified'
  | 'isConnectable'
  | 'locationName'
  | 'luid'
  | 'modifiedTime'
  | 'ownerId'
  | 'ownerName'
  | 'parentWorkbookName'
  | 'projectId'
  | 'projectName'
  | 'sheetType'
  | 'tags'
  | 'title'
  | 'totalViewCount'
  | 'viewCountLastMonth'
  | 'type'
  | 'workbookDescription';

function getReducedSearchItemContent(
  content: Record<string, unknown>,
): ReducedSearchContentResponse {
  const r: ReducedSearchContentResponse = {};
  if (content.modifiedTime) r.modifiedTime = content.modifiedTime;
  if (content.sheetType) r.sheetType = content.sheetType;
  if (content.caption) r.caption = content.caption;
  if (content.workbookDescription) r.workbookDescription = content.workbookDescription;
  if (content.type) r.type = content.type;
  if (content.ownerId) r.ownerId = content.ownerId;
  if (content.title) r.title = content.title;
  if (content.ownerName) r.ownerName = content.ownerName;
  if (content.containerName) {
    if (content.type === 'view') {
      r.parentWorkbookName = content.containerName;
    } else {
      r.containerName = content.containerName;
    }
  }
  if (content.luid) r.luid = content.luid;
  if (content.locationName) r.locationName = content.locationName;
  if (Array.isArray(content.comments) && content.comments.length) r.comments = content.comments;
  if (content.hitsTotal != undefined) r.totalViewCount = content.hitsTotal;
  if (content.favoritesTotal != undefined) r.favoritesTotal = content.favoritesTotal;
  if (Array.isArray(content.tags) && content.tags.length) r.tags = content.tags;
  if (content.projectId) r.projectId = content.projectId;
  if (content.projectName) r.projectName = content.projectName;
  if (content.hitsSmallSpanTotal != undefined) r.viewCountLastMonth = content.hitsSmallSpanTotal;
  if (content.downstreamWorkbookCount != undefined) r.downstreamWorkbookCount = content.downstreamWorkbookCount;
  if (content.isConnectable != undefined) r.isConnectable = content.isConnectable;
  if (content.datasourceIsPublished != undefined) r.datasourceIsPublished = content.datasourceIsPublished;
  if (content.connectionType) r.connectionType = content.connectionType;
  if (content.isCertified != undefined) r.isCertified = content.isCertified;
  if (content.hasExtracts != undefined) r.hasExtracts = content.hasExtracts;
  if (content.extractRefreshedAt) r.extractRefreshedAt = content.extractRefreshedAt;
  if (content.extractUpdatedAt) r.extractUpdatedAt = content.extractUpdatedAt;
  if (content.connectedWorkbooksCount != undefined) r.connectedWorkbooksCount = content.connectedWorkbooksCount;
  if (content.extractCreationPending != undefined) r.extractCreationPending = content.extractCreationPending;
  if (content.hasSevereDataQualityWarning != undefined) r.hasSevereDataQualityWarning = content.hasSevereDataQualityWarning;
  if (content.datasourceLuid) r.datasourceLuid = content.datasourceLuid;
  if (content.hasActiveDataQualityWarning != undefined) r.hasActiveDataQualityWarning = content.hasActiveDataQualityWarning;
  return r;
}

export function reduceSearchContentResponse(
  response: SearchContentResponse,
): Array<ReducedSearchContentResponse> {
  let searchResults: Array<ReducedSearchContentResponse> = [];
  if (response.items) {
    for (const item of response.items) {
      searchResults.push(getReducedSearchItemContent(item.content as Record<string, unknown>));
    }
  }

  // Remove duplicate datasources with luid matching a unifieddatasource's datasourceLuid
  const unifiedDatasourceLuids = new Set(
    searchResults
      .filter((item) => item.type === 'unifieddatasource')
      .map((item) => item.datasourceLuid)
      .filter((luid): luid is string => typeof luid === 'string'),
  );

  searchResults = searchResults.filter((item) => {
    if (item.type === 'datasource') {
      return typeof item.luid === 'string' && !unifiedDatasourceLuids.has(item.luid);
    }
    return true;
  });

  // Normalize unifieddatasource entries to datasource entries
  for (const item of searchResults) {
    if (item.type === 'unifieddatasource') {
      item.type = 'datasource';
      item.luid = item.datasourceLuid;
      delete item.datasourceLuid;
    }
  }

  return searchResults;
}
