import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import { processChatWebSocketMessage } from './processChatWebSocketMessage';
import type { ChatWebSocketProcessContext } from './processChatWebSocketMessage';
import type { MessageResponse } from '../../types/api';
import type { ChatListRow } from '../../types/chatList';
import type { PartnerPresence } from '../../api/presence';
import { TYPING_DISPLAY_TIMEOUT_MS } from './messageThread.constants';

vi.mock('../../api/chat', () => ({
  markConversationRead: vi.fn(() => Promise.resolve()),
}));

import { markConversationRead } from '../../api/chat';

function makeCtx(overrides: Partial<ChatWebSocketProcessContext> = {}): ChatWebSocketProcessContext {
  return {
    cid: 'conv-1',
    userId: 'u-me',
    refreshUnread: vi.fn(),
    partnerIdRef: { current: 'partner-1' } as MutableRefObject<string | undefined>,
    setMessages: vi.fn(),
    setPartnerTyping: vi.fn(),
    setPartnerTypingName: vi.fn(),
    setPartnerPresence: vi.fn(),
    setConversationRead: vi.fn(),
    typingHideTimeoutRef: { current: null },
    outboundPendingRef: { current: null },
    ...overrides,
  };
}

describe('processChatWebSocketMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('calls refreshUnread on unread_count', () => {
    const ctx = makeCtx();
    processChatWebSocketMessage({ type: 'unread_count' }, ctx);
    expect(ctx.refreshUnread).toHaveBeenCalledTimes(1);
  });

  it('sets partner offline when user_offline matches partner', () => {
    const setPartnerPresence = vi.fn() as Dispatch<SetStateAction<PartnerPresence | null>>;
    const ctx = makeCtx({ setPartnerPresence });
    processChatWebSocketMessage({ type: 'user_offline', user_id: 'partner-1' }, ctx);
    expect(setPartnerPresence).toHaveBeenCalledTimes(1);
    const updater = (setPartnerPresence as ReturnType<typeof vi.fn>).mock.calls[0][0] as (p: {
      online: boolean;
      last_seen: string | null;
    }) => { online: boolean; last_seen: string | null };
    expect(updater({ online: true, last_seen: 'ts' })).toEqual({
      online: false,
      last_seen: 'ts',
    });
  });

  it('ignores user_offline for other users', () => {
    const ctx = makeCtx();
    processChatWebSocketMessage({ type: 'user_offline', user_id: 'someone-else' }, ctx);
    expect(ctx.setPartnerPresence).not.toHaveBeenCalled();
  });

  it('handles user_online for partner', () => {
    const setPartnerPresence = vi.fn() as Dispatch<SetStateAction<PartnerPresence | null>>;
    processChatWebSocketMessage(
      { type: 'user_online', user_id: 'partner-123' },
      { ...makeCtx(), partnerIdRef: { current: 'partner-123' }, setPartnerPresence }
    );
    expect(setPartnerPresence).toHaveBeenCalledWith(expect.any(Function));
  });

  it('marks conversation read and refreshes unread when message targets this conversation', async () => {
    const ctx = makeCtx();
    processChatWebSocketMessage(
      {
        message_id: 9,
        conversation_id: 'conv-1',
        sender_id: 'partner-1',
        body: 'hi',
        created_at: '2020-01-01',
      } satisfies MessageResponse as unknown as Record<string, unknown>,
      ctx
    );
    expect(markConversationRead).toHaveBeenCalledWith('conv-1');
    await vi.runAllTimersAsync();
    expect(ctx.refreshUnread).toHaveBeenCalled();
  });

  it('appends message and clears partner typing when sender is partner', () => {
    const setMessages = vi.fn() as Dispatch<SetStateAction<ChatListRow[]>>;
    const ctx = makeCtx({ setMessages });
    const msg: MessageResponse = {
      message_id: 3,
      conversation_id: 'conv-1',
      sender_id: 'partner-1',
      body: 'hello',
      created_at: 't',
    };
    processChatWebSocketMessage(msg as unknown as Record<string, unknown>, ctx);
    expect(setMessages).toHaveBeenCalled();
    const updater = (setMessages as ReturnType<typeof vi.fn>).mock.calls[0][0] as (
      p: ChatListRow[]
    ) => ChatListRow[];
    expect(updater([])).toEqual([{ kind: 'confirmed', message: msg }]);
    expect(ctx.setPartnerTyping).toHaveBeenCalledWith(false);
  });

  it('does not clear partner typing when message is from self', () => {
    const ctx = makeCtx();
    const msg: MessageResponse = {
      message_id: 3,
      conversation_id: 'conv-1',
      sender_id: 'u-me',
      body: 'me',
      created_at: 't',
    };
    processChatWebSocketMessage(msg as unknown as Record<string, unknown>, ctx);
    expect(ctx.setPartnerTyping).not.toHaveBeenCalled();
  });

  it('typing_start from other user sets typing and clears after timeout', () => {
    const ctx = makeCtx();
    processChatWebSocketMessage(
      {
        type: 'typing_start',
        user_id: 'partner-1',
        full_name: 'Bob',
        conversation_id: 'conv-1',
        recipient_id: 'recipient-123',
      },
      ctx
    );
    expect(ctx.setPartnerTyping).toHaveBeenCalledWith(true);
    expect(ctx.setPartnerTypingName).toHaveBeenCalledWith('Bob');
    vi.advanceTimersByTime(TYPING_DISPLAY_TIMEOUT_MS);
    expect(ctx.setPartnerTyping).toHaveBeenLastCalledWith(false);
    expect(ctx.setPartnerTypingName).toHaveBeenLastCalledWith(null);
  });

  it('ignores typing_start for other conversation', () => {
    const ctx = makeCtx();
    processChatWebSocketMessage(
      {
        type: 'typing_start',
        user_id: 'partner-1',
        full_name: 'Bob',
        conversation_id: 'conv-2',
        recipient_id: 'recipient-123',
      },
      ctx
    );
    expect(ctx.setPartnerTyping).not.toHaveBeenCalled();
  });

  it('typing_stop clears typing and pending timeout', () => {
    const ctx = makeCtx();
    processChatWebSocketMessage(
      {
        type: 'typing_start',
        user_id: 'partner-1',
        full_name: 'Bob',
        conversation_id: 'conv-1',
        recipient_id: 'recipient-123',
      },
      ctx
    );
    vi.clearAllMocks();
    processChatWebSocketMessage(
      {
        type: 'typing_stop',
        conversation_id: 'conv-1',
        recipient_id: 'recipient-123',
        user_id: 'partner-1',
      },
      ctx
    );
    expect(ctx.setPartnerTyping).toHaveBeenCalledWith(false);
    expect(ctx.setPartnerTypingName).toHaveBeenCalledWith(null);
    vi.advanceTimersByTime(TYPING_DISPLAY_TIMEOUT_MS);
    expect(ctx.setPartnerTyping).toHaveBeenCalledTimes(1);
  });

  it('sets conversation read on message_read from partner in same conversation', () => {
    const ctx = makeCtx();
    processChatWebSocketMessage(
      {
        type: 'message_read',
        conversation_id: 'conv-1',
        reader_id: 'partner-1',
        read_up_to_message_id: 42,
      },
      ctx
    );
    expect(ctx.setConversationRead).toHaveBeenCalledWith(42);
  });

  it('dedupes repeated message frames by message_id', () => {
    const setMessages = vi.fn() as Dispatch<SetStateAction<ChatListRow[]>>;
    const ctx = makeCtx({ setMessages });
    const msg: MessageResponse = {
      message_id: 3,
      conversation_id: 'conv-1',
      sender_id: 'partner-1',
      body: 'hello',
      created_at: 't',
    };
    processChatWebSocketMessage(msg as unknown as Record<string, unknown>, ctx);
    const updater = (setMessages as ReturnType<typeof vi.fn>).mock.calls[0][0] as (
      p: ChatListRow[]
    ) => ChatListRow[];
    const prev: ChatListRow[] = [{ kind: 'confirmed', message: msg }];
    expect(updater(prev)).toEqual(prev);
  });

  it('own message from WS drops matching pending and appends confirmed once', () => {
    const outboundPendingRef = {
      current: { client_message_id: 'cid-1', body: 'hello' },
    } as MutableRefObject<{ client_message_id: string; body: string } | null>;
    const setMessages = vi.fn() as Dispatch<SetStateAction<ChatListRow[]>>;
    const ctx = makeCtx({ setMessages, outboundPendingRef, userId: 'u-me' });
    const msg: MessageResponse = {
      message_id: 3,
      conversation_id: 'conv-1',
      sender_id: 'u-me',
      body: 'hello',
      created_at: 't',
    };
    processChatWebSocketMessage(msg as unknown as Record<string, unknown>, ctx);
    const updater = (setMessages as ReturnType<typeof vi.fn>).mock.calls[0][0] as (
      p: ChatListRow[]
    ) => ChatListRow[];
    const prev: ChatListRow[] = [
      { kind: 'pending', client_message_id: 'cid-1', conversation_id: 'conv-1', sender_id: 'u-me', body: 'hello', created_at: 't0' },
    ];
    expect(updater(prev)).toEqual([{ kind: 'confirmed', message: msg }]);
    expect(outboundPendingRef.current).toBeNull();
    processChatWebSocketMessage(msg as unknown as Record<string, unknown>, ctx);
    const updater2 = (setMessages as ReturnType<typeof vi.fn>).mock.calls[1][0] as (
      p: ChatListRow[]
    ) => ChatListRow[];
    const afterFirst = [{ kind: 'confirmed', message: msg }] as ChatListRow[];
    expect(updater2(afterFirst)).toEqual(afterFirst);
  });

  it('ignores message_read for self or other conversation', () => {
    const ctx = makeCtx();
    processChatWebSocketMessage(
      { type: 'message_read', conversation_id: 'conv-1', reader_id: 'u-me' },
      ctx
    );
    processChatWebSocketMessage(
      {
        type: 'message_read',
        conversation_id: 'conv-2',
        reader_id: 'partner-1',
        read_up_to_message_id: 42,
      },
      ctx
    );
    processChatWebSocketMessage(
      {
        type: 'message_read',
        conversation_id: 'conv-1',
        reader_id: 'partner-1',
      },
      ctx
    );
    expect(ctx.setConversationRead).not.toHaveBeenCalled();
  });
});
