import { describe, expect, it } from 'vitest';

import { chatReducer, initialChatState } from './chatState';

describe('chatReducer', () => {
  it('OPEN_POPUP clears panel', () => {
    const s = {
      ...initialChatState,
      panelConversationId: 'p1',
    };
    const next = chatReducer(s, { type: 'OPEN_POPUP', conversationId: 'c1' });
    expect(next.openConversationId).toBe('c1');
    expect(next.panelConversationId).toBeNull();
  });

  it('OPEN_PANEL clears popup', () => {
    const s = { ...initialChatState, openConversationId: 'c1' };
    const next = chatReducer(s, { type: 'OPEN_PANEL', conversationId: 'p1' });
    expect(next.panelConversationId).toBe('p1');
    expect(next.openConversationId).toBeNull();
  });

  it('SET_UNREAD_MESSAGES', () => {
    const next = chatReducer(initialChatState, { type: 'SET_UNREAD_MESSAGES', count: 3 });
    expect(next.unreadMessages).toBe(3);
  });

  it('DECREMENT_UNREAD_NOTIFICATIONS floors at 0', () => {
    const next = chatReducer(
      { ...initialChatState, unreadNotifications: 0 },
      { type: 'DECREMENT_UNREAD_NOTIFICATIONS' }
    );
    expect(next.unreadNotifications).toBe(0);
  });

  it('SET_NOTIFICATION_STATE uses server-provided unreadCount', () => {
    const list = [
      {
        type: 'x',
        title: 't',
        body: null,
        created_at: '2020-01-01',
        booking_id: 'b1',
        ride_id: 'r1',
        other_party_name: null,
        ride_origin: null,
        ride_destination: null,
        status: null,
        is_read: false,
      },
    ];
    const next = chatReducer(initialChatState, { type: 'SET_NOTIFICATION_STATE', list, unreadCount: 1 });
    expect(next.notificationList).toHaveLength(1);
    expect(next.unreadNotifications).toBe(1);
  });

  it('RESET_SESSION', () => {
    const s = {
      ...initialChatState,
      unreadMessages: 5,
      openConversationId: 'x',
    };
    const next = chatReducer(s, { type: 'RESET_SESSION' });
    expect(next).toEqual(initialChatState);
  });

  it('CLOSE_ALL_CHATS clears both popup and panel', () => {
    const s = {
      ...initialChatState,
      openConversationId: 'a',
      panelConversationId: 'b',
    };
    const next = chatReducer(s, { type: 'CLOSE_ALL_CHATS' });
    expect(next.openConversationId).toBeNull();
    expect(next.panelConversationId).toBeNull();
  });

  it('MARK_ALL_NOTIFICATIONS_READ sets unread to 0', () => {
    const s = { ...initialChatState, unreadNotifications: 4 };
    const next = chatReducer(s, { type: 'MARK_ALL_NOTIFICATIONS_READ' });
    expect(next.unreadNotifications).toBe(0);
  });
});
