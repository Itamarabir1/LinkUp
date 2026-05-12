import { api } from './client';
import type {
  ConversationDetail,
  ConversationListItem,
  MessageGapResponse,
  MessageResponse,
  PaginatedConversationsResponse,
  PaginatedMessagesResponse,
} from '../types/api';

export type { ConversationDetail, ConversationListItem, MessageResponse };

export async function openChatByBooking(bookingId: string): Promise<ConversationDetail> {
  const { data } = await api.post<ConversationDetail>(`/chat/conversations/by-booking/${bookingId}`);
  return data;
}

const DEFAULT_INBOX_LIMIT = 30;

export async function listConversations(
  params?: { limit?: number; after?: string },
  opts?: { signal?: AbortSignal },
): Promise<PaginatedConversationsResponse> {
  const limit = params?.limit ?? DEFAULT_INBOX_LIMIT;
  const { data } = await api.get<PaginatedConversationsResponse>('/chat/conversations', {
    params: {
      limit,
      ...(params?.after ? { after: params.after } : {}),
    },
    signal: opts?.signal,
  });
  return {
    items: data.items ?? [],
    has_more: data.has_more ?? false,
    next_cursor: data.next_cursor ?? null,
  };
}

export const inboxPageSizeDefault = DEFAULT_INBOX_LIMIT;

export function getConversation(conversationId: string, opts?: { signal?: AbortSignal }) {
  return api.get<ConversationDetail>(`/chat/conversations/${conversationId}`, { signal: opts?.signal });
}

export function getMessages(conversationId: string, params?: { limit?: number; after?: string; signal?: AbortSignal }) {
  const { signal, ...rest } = params ?? {};
  return api.get<PaginatedMessagesResponse>(`/chat/conversations/${conversationId}/messages`, { params: rest, signal });
}

export function getMessagesGap(conversationId: string, since_message_id: number, opts?: { signal?: AbortSignal }) {
  return api.get<MessageGapResponse>(`/chat/conversations/${conversationId}/messages/gap`, {
    params: { since_message_id },
    signal: opts?.signal,
  });
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

export function fetchUnreadMessageCount(opts?: { signal?: AbortSignal }) {
  return api.get<{ count: number }>('/chat/unread-count', { signal: opts?.signal });
}
