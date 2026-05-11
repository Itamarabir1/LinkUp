import { describe, expect, it, vi, beforeEach } from 'vitest';
import type { MessageResponse } from '../../types/api';
import { fetchMissedGap } from './fetchMissedGap';

const getMessagesGap = vi.fn();

vi.mock('../../api/chat', () => ({
  getMessagesGap: (...args: unknown[]) => getMessagesGap(...args),
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
    getMessagesGap.mockReset();
  });

  it('returns empty when first page has no items', async () => {
    getMessagesGap.mockResolvedValue({ data: { items: [], truncated: false, last_message_id: null } });
    const r = await fetchMissedGap('conv-1', 100);
    expect(r.messages).toEqual([]);
    expect(r.incomplete).toBe(false);
    expect(getMessagesGap).toHaveBeenCalledTimes(1);
    expect(getMessagesGap).toHaveBeenCalledWith('conv-1', 100);
  });

  it('fetches one page when truncated is false', async () => {
    getMessagesGap.mockResolvedValue({
      data: {
        items: [msg(101), msg(102)],
        truncated: false,
        last_message_id: null,
      },
    });
    const r = await fetchMissedGap('conv-1', 100);
    expect(r.messages.map((m) => m.message_id)).toEqual([101, 102]);
    expect(r.incomplete).toBe(false);
    expect(getMessagesGap).toHaveBeenCalledTimes(1);
  });

  it('paginates with last_message_id until truncated is false', async () => {
    getMessagesGap
      .mockResolvedValueOnce({
        data: {
          items: [msg(130), msg(129)],
          truncated: true,
          last_message_id: 130,
        },
      })
      .mockResolvedValueOnce({
        data: {
          items: [msg(128), msg(127)],
          truncated: false,
          last_message_id: null,
        },
      });
    const r = await fetchMissedGap('conv-1', 100);
    expect(r.messages.map((m) => m.message_id)).toEqual([127, 128, 129, 130]);
    expect(r.incomplete).toBe(false);
    expect(getMessagesGap).toHaveBeenCalledTimes(2);
    expect(getMessagesGap).toHaveBeenNthCalledWith(1, 'conv-1', 100);
    expect(getMessagesGap).toHaveBeenNthCalledWith(2, 'conv-1', 130);
  });

  it('dedupes message_id across pages', async () => {
    const shared = msg(128);
    getMessagesGap
      .mockResolvedValueOnce({
        data: {
          items: [msg(130), shared],
          truncated: true,
          last_message_id: 130,
        },
      })
      .mockResolvedValueOnce({
        data: {
          items: [shared, msg(127)],
          truncated: false,
          last_message_id: null,
        },
      });
    const r = await fetchMissedGap('conv-1', 100);
    expect(r.messages.map((m) => m.message_id)).toEqual([127, 128, 130]);
  });

  it('sets incomplete when maxPages is reached while server still has more', async () => {
    getMessagesGap.mockResolvedValue({
      data: {
        items: [msg(201)],
        truncated: true,
        last_message_id: 201,
      },
    });
    const r = await fetchMissedGap('conv-1', 100, { maxPages: 1 });
    expect(r.messages.map((m) => m.message_id)).toEqual([201]);
    expect(r.incomplete).toBe(true);
    expect(getMessagesGap).toHaveBeenCalledTimes(1);
  });

  it('stops before next page when shouldAbort returns true after first chunk', async () => {
    const shouldAbort = vi.fn()
      .mockReturnValueOnce(false)
      .mockReturnValueOnce(false)
      .mockReturnValue(true);
    getMessagesGap.mockResolvedValueOnce({
      data: {
        items: [msg(201)],
        truncated: true,
        last_message_id: 201,
      },
    });
    const r = await fetchMissedGap('conv-1', 100, { shouldAbort });
    expect(r.messages.map((m) => m.message_id)).toEqual([201]);
    expect(r.incomplete).toBe(true);
    expect(getMessagesGap).toHaveBeenCalledTimes(1);
  });

  it('retries failed page then succeeds', async () => {
    getMessagesGap
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({
        data: {
          items: [msg(301)],
          truncated: false,
          last_message_id: null,
        },
      });
    const r = await fetchMissedGap('conv-1', 200);
    expect(r.messages.map((m) => m.message_id)).toEqual([301]);
    expect(r.incomplete).toBe(false);
    expect(getMessagesGap).toHaveBeenCalledTimes(2);
  });

  it('returns incomplete empty when first page fails after retries', async () => {
    getMessagesGap.mockRejectedValue(new Error('network'));
    const r = await fetchMissedGap('conv-1', 50);
    expect(r.messages).toEqual([]);
    expect(r.incomplete).toBe(true);
    expect(getMessagesGap).toHaveBeenCalledTimes(3);
  });
});
