import { getMessages } from '../../api/chat';
import type { MessageResponse, PaginatedMessagesResponse } from '../../types/api';

const DEFAULT_PAGE_SIZE = 30;
/** Safety cap: 50 pages × 30 = 1500 messages max per reconnect backfill. */
const DEFAULT_MAX_PAGES = 50;
const RETRIES_PER_PAGE = 2;
const RETRY_BASE_MS = 400;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export interface FetchMissedGapOptions {
  pageSize?: number;
  /** Max HTTP pages (first `after` + continued `before`); default 50. */
  maxPages?: number;
  /** Return true to stop after current page and mark `incomplete` (e.g. conversation changed). */
  shouldAbort?: () => boolean;
}

export interface FetchMissedGapResult {
  messages: MessageResponse[];
  /** True if gap may remain (error, abort, or hit maxPages while server still has more). */
  incomplete: boolean;
}

function addToMap(map: Map<number, MessageResponse>, items: MessageResponse[]) {
  for (const m of items) {
    map.set(m.message_id, m);
  }
}

async function fetchPageWithRetry(
  conversationId: string,
  pageSize: number,
  params: { after?: number; before?: number },
  shouldAbort?: () => boolean
): Promise<PaginatedMessagesResponse> {
  let lastErr: unknown;
  for (let attempt = 0; attempt <= RETRIES_PER_PAGE; attempt++) {
    if (shouldAbort?.()) {
      throw new Error('fetchMissedGap:aborted');
    }
    try {
      const res = await getMessages(conversationId, {
        limit: pageSize,
        ...(params.after !== undefined ? { after: params.after } : {}),
        ...(params.before !== undefined ? { before: params.before } : {}),
      });
      return res.data ?? { items: [], has_more: false, next_cursor: null };
    } catch (e) {
      lastErr = e;
      if (attempt < RETRIES_PER_PAGE) {
        await sleep(RETRY_BASE_MS * (attempt + 1));
      }
    }
  }
  throw lastErr;
}

/**
 * Loads all messages in the "gap" after `afterMessageId` using the same pagination
 * contract as the backend: first `GET ...?after=`, then `GET ...?before=next_cursor`
 * while `has_more` (newest chunk first, then older chunks toward the anchor).
 */
export async function fetchMissedGap(
  conversationId: string,
  afterMessageId: number,
  options: FetchMissedGapOptions = {}
): Promise<FetchMissedGapResult> {
  const pageSize = options.pageSize ?? DEFAULT_PAGE_SIZE;
  const maxPages = options.maxPages ?? DEFAULT_MAX_PAGES;
  const shouldAbort = options.shouldAbort;

  const byId = new Map<number, MessageResponse>();
  let incomplete = false;
  let pageCount = 0;

  let data: PaginatedMessagesResponse;

  try {
    data = await fetchPageWithRetry(conversationId, pageSize, { after: afterMessageId }, shouldAbort);
  } catch (e) {
    if ((e as Error)?.message === 'fetchMissedGap:aborted') {
      return { messages: [], incomplete: true };
    }
    return { messages: [], incomplete: true };
  }

  pageCount += 1;
  addToMap(byId, data.items ?? []);

  while (data.has_more && data.next_cursor && pageCount < maxPages) {
    if (shouldAbort?.()) {
      incomplete = true;
      break;
    }
    const before = parseInt(data.next_cursor, 10);
    if (!Number.isFinite(before)) {
      break;
    }
    try {
      data = await fetchPageWithRetry(conversationId, pageSize, { before }, shouldAbort);
    } catch (e) {
      if ((e as Error)?.message === 'fetchMissedGap:aborted') {
        incomplete = true;
        break;
      }
      incomplete = true;
      break;
    }
    pageCount += 1;
    addToMap(byId, data.items ?? []);
  }

  if (pageCount >= maxPages && data.has_more && data.next_cursor) {
    incomplete = true;
  }

  const messages = [...byId.values()].sort((a, b) => a.message_id - b.message_id);
  return { messages, incomplete };
}
