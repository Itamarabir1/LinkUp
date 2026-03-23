import type { NotificationItem } from '../types/api';
import { getNotificationItemKey, getReadNotificationSet } from './chatNotificationStorage';

export type ChatState = {
  openConversationId: string | null;
  panelConversationId: string | null;
  unreadMessages: number;
  unreadNotifications: number;
  notificationList: NotificationItem[];
};

export const initialChatState: ChatState = {
  openConversationId: null,
  panelConversationId: null,
  unreadMessages: 0,
  unreadNotifications: 0,
  notificationList: [],
};

export type ChatAction =
  | { type: 'OPEN_POPUP'; conversationId: string }
  | { type: 'OPEN_PANEL'; conversationId: string }
  | { type: 'CLOSE_ALL_CHATS' }
  | { type: 'SET_UNREAD_MESSAGES'; count: number }
  | { type: 'SET_NOTIFICATION_STATE'; list: NotificationItem[] }
  | { type: 'RESET_SESSION' }
  | { type: 'DECREMENT_UNREAD_NOTIFICATIONS' }
  | { type: 'MARK_ALL_NOTIFICATIONS_READ' };

function countUnreadFromList(list: NotificationItem[]): number {
  const readSet = getReadNotificationSet();
  return list.filter((n) => !readSet.has(getNotificationItemKey(n))).length;
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'OPEN_POPUP':
      return {
        ...state,
        openConversationId: action.conversationId,
        panelConversationId: null,
      };
    case 'OPEN_PANEL':
      return {
        ...state,
        panelConversationId: action.conversationId,
        openConversationId: null,
      };
    case 'CLOSE_ALL_CHATS':
      return { ...state, openConversationId: null, panelConversationId: null };
    case 'SET_UNREAD_MESSAGES':
      return { ...state, unreadMessages: action.count };
    case 'SET_NOTIFICATION_STATE':
      return {
        ...state,
        notificationList: action.list,
        unreadNotifications: countUnreadFromList(action.list),
      };
    case 'RESET_SESSION':
      return { ...initialChatState };
    case 'DECREMENT_UNREAD_NOTIFICATIONS':
      return { ...state, unreadNotifications: Math.max(0, state.unreadNotifications - 1) };
    case 'MARK_ALL_NOTIFICATIONS_READ':
      return { ...state, unreadNotifications: 0 };
    default:
      return state;
  }
}
