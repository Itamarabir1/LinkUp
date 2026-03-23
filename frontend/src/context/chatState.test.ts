import { describe, expect, it, vi } from 'vitest';

vi.mock('./chatNotificationStorage', () => ({
  getReadNotificationSet: () => new Set<string>(),
  getNotificationItemKey: (n: { booking_id: string }) => n.booking_id,
}));

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

  it('SET_NOTIFICATION_STATE counts unread when read set empty', () => {
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
      },
    ];
    const next = chatReducer(initialChatState, { type: 'SET_NOTIFICATION_STATE', list });
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
});
