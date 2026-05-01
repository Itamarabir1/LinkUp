import { describe, expect, it, vi, beforeEach } from 'vitest';
import type { MessageResponse } from '../../types/api';
import { fetchMissedGap } from './fetchMissedGap';

const getMessages = vi.fn();

vi.mock('../../api/chat', () => ({
  getMessages: (...args: unknown[]) => getMessages(...args),
}));

function msg(id: number): MessageResponse {
  return {
    message_id: id,
    conversation_id: 'conv-1',
    sender_id: 'user-1',
    body: `body-${id}`,
    created_at: '2026-01-01T00:00:00Z',
  };
}

describe('fetchMissedGap', () => {
  beforeEach(() => {
    getMessages.mockReset();
  });

  it('returns empty when first page has no items', async () => {
    getMessages.mockResolvedValue({ data: { items: [], has_more: false, next_cursor: null } });
    const r = await fetchMissedGap('conv-1', 100);
    expect(r.messages).toEqual([]);
    expect(r.incomplete).toBe(false);
    expect(getMessages).toHaveBeenCalledTimes(1);
    expect(getMessages).toHaveBeenCalledWith('conv-1', { limit: 30, after: 100 });
  });

  it('fetches one page when has_more is false', async () => {
    getMessages.mockResolvedValue({
      data: {
        items: [msg(101), msg(102)],
        has_more: false,
        next_cursor: null,
      },
    });
    const r = await fetchMissedGap('conv-1', 100);
    expect(r.messages.map((m) => m.message_id)).toEqual([101, 102]);
    expect(r.incomplete).toBe(false);
    expect(getMessages).toHaveBeenCalledTimes(1);
  });

  it('paginates with before=next_cursor until has_more is false', async () => {
    getMessages
      .mockResolvedValueOnce({
        data: {
          items: [msg(130), msg(129)],
          has_more: true,
          next_cursor: '128',
        },
      })
      .mockResolvedValueOnce({
        data: {
          items: [msg(128), msg(127)],
          has_more: false,
          next_cursor: null,
        },
      });
    const r = await fetchMissedGap('conv-1', 100);
    expect(r.messages.map((m) => m.message_id)).toEqual([127, 128, 129, 130]);
    expect(r.incomplete).toBe(false);
    expect(getMessages).toHaveBeenCalledTimes(2);
    expect(getMessages).toHaveBeenNthCalledWith(1, 'conv-1', { limit: 30, after: 100 });
    expect(getMessages).toHaveBeenNthCalledWith(2, 'conv-1', { limit: 30, before: 128 });
  });

  it('dedupes message_id across pages', async () => {
    const shared = msg(128);
    getMessages
      .mockResolvedValueOnce({
        data: {
          items: [msg(130), shared],
          has_more: true,
          next_cursor: '128',
        },
      })
      .mockResolvedValueOnce({
        data: {
          items: [shared, msg(127)],
          has_more: false,
          next_cursor: null,
        },
      });
    const r = await fetchMissedGap('conv-1', 100);
    expect(r.messages.map((m) => m.message_id)).toEqual([127, 128, 130]);
  });

  it('sets incomplete when maxPages is reached while server still has more', async () => {
    getMessages.mockResolvedValue({
      data: {
        items: [msg(201)],
        has_more: true,
        next_cursor: '200',
      },
    });
    const r = await fetchMissedGap('conv-1', 100, { maxPages: 1 });
    expect(r.messages.map((m) => m.message_id)).toEqual([201]);
    expect(r.incomplete).toBe(true);
    expect(getMessages).toHaveBeenCalledTimes(1);
  });

  it('stops before next page when shouldAbort returns true after first chunk', async () => {
    const shouldAbort = vi.fn().mockReturnValueOnce(false).mockReturnValue(true);
    getMessages.mockResolvedValueOnce({
      data: {
        items: [msg(201)],
        has_more: true,
        next_cursor: '200',
      },
    });
    const r = await fetchMissedGap('conv-1', 100, { shouldAbort });
    expect(r.messages.map((m) => m.message_id)).toEqual([201]);
    expect(r.incomplete).toBe(true);
    expect(getMessages).toHaveBeenCalledTimes(1);
  });

  it('retries failed page then succeeds', async () => {
    getMessages
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({
        data: {
          items: [msg(301)],
          has_more: false,
          next_cursor: null,
        },
      });
    const r = await fetchMissedGap('conv-1', 200);
    expect(r.messages.map((m) => m.message_id)).toEqual([301]);
    expect(r.incomplete).toBe(false);
    expect(getMessages).toHaveBeenCalledTimes(2);
  });

  it('returns incomplete empty when first page fails after retries', async () => {
    getMessages.mockRejectedValue(new Error('network'));
    const r = await fetchMissedGap('conv-1', 50);
    expect(r.messages).toEqual([]);
    expect(r.incomplete).toBe(true);
    expect(getMessages).toHaveBeenCalledTimes(3);
  });
});
