import { api } from './client';
import type {
  ConversationDetail,
  ConversationListItem,
  MessageResponse,
  PaginatedMessagesResponse,
} from '../types/api';

export type { ConversationDetail, ConversationListItem, MessageResponse };

export async function openChatByBooking(bookingId: string): Promise<ConversationDetail> {
  const { data } = await api.post<ConversationDetail>(`/chat/conversations/by-booking/${bookingId}`);
  return data;
}

export function listConversations() {
  return api.get<ConversationListItem[]>('/chat/conversations');
}

export function getConversation(conversationId: string) {
  return api.get<ConversationDetail>(`/chat/conversations/${conversationId}`);
}

export function getMessages(conversationId: string, params?: { limit?: number; before?: number; after?: number }) {
  return api.get<PaginatedMessagesResponse>(`/chat/conversations/${conversationId}/messages`, { params });
}

export function sendMessage(conversationId: string, body: string, idempotencyKey?: string) {
  const key = idempotencyKey ?? crypto.randomUUID();
  return api.post<MessageResponse>(`/chat/conversations/${conversationId}/messages`, { body }, {
    headers: {
      'Idempotency-Key': key,
    },
  });
}

export function markConversationRead(conversationId: string) {
  return api.post(`/chat/conversations/${conversationId}/read`);
}

export function fetchUnreadMessageCount() {
  return api.get<{ count: number }>('/chat/unread-count');
}
