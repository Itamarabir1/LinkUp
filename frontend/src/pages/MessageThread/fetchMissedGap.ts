import { getMessagesGap } from '../../api/chat';
import type { MessageResponse } from '../../types/api';

const DEFAULT_MAX_PAGES = 50;
const RETRIES_PER_BATCH = 2;
const RETRY_BASE_MS = 400;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export interface FetchMissedGapOptions {
  /** Max HTTP batches for truncated reconnect responses; default 50. */
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

async function fetchGapWithRetry(
  conversationId: string,
  sinceMessageId: number,
  shouldAbort?: () => boolean
): Promise<{ items: MessageResponse[]; truncated: boolean; last_message_id: number | null }> {
  let lastErr: unknown;
  for (let attempt = 0; attempt <= RETRIES_PER_BATCH; attempt++) {
    if (shouldAbort?.()) {
      throw new Error('fetchMissedGap:aborted');
    }
    try {
      const res = await getMessagesGap(conversationId, sinceMessageId);
      return res.data ?? { items: [], truncated: false, last_message_id: null };
    } catch (e) {
      lastErr = e;
      if (attempt < RETRIES_PER_BATCH) {
        await sleep(RETRY_BASE_MS * (attempt + 1));
      }
    }
  }
  throw lastErr;
}

/**
 * Loads all messages in the reconnect "gap" from the dedicated gap endpoint.
 * Repeats while server reports truncation using last_message_id as the next anchor.
 */
export async function fetchMissedGap(
  conversationId: string,
  afterMessageId: number,
  options: FetchMissedGapOptions = {}
): Promise<FetchMissedGapResult> {
  const maxPages = options.maxPages ?? DEFAULT_MAX_PAGES;
  const shouldAbort = options.shouldAbort;

  const byId = new Map<number, MessageResponse>();
  let incomplete = false;
  let batchCount = 0;
  let sinceMessageId = afterMessageId;

  while (batchCount < maxPages) {
    if (shouldAbort?.()) {
      incomplete = true;
      break;
    }
    let data: { items: MessageResponse[]; truncated: boolean; last_message_id: number | null };
    try {
      data = await fetchGapWithRetry(conversationId, sinceMessageId, shouldAbort);
    } catch (e) {
      if ((e as Error)?.message === 'fetchMissedGap:aborted') {
        incomplete = true;
        break;
      }
      incomplete = true;
      break;
    }
    batchCount += 1;
    addToMap(byId, data.items ?? []);

    if (!data.truncated) {
      break;
    }
    if (data.last_message_id == null || data.last_message_id <= sinceMessageId) {
      incomplete = true;
      break;
    }
    sinceMessageId = data.last_message_id;
  }

  if (batchCount >= maxPages) {
    incomplete = true;
  }

  const messages = [...byId.values()].sort((a, b) => a.message_id - b.message_id);
  return { messages, incomplete };
}
