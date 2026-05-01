import type { MessageResponse } from './api';

export interface ChatConfirmedRow {
  kind: 'confirmed';
  message: MessageResponse;
}

export interface ChatPendingRow {
  kind: 'pending';
  client_message_id: string;
  conversation_id: string;
  sender_id: string;
  body: string;
  created_at: string;
}

export type ChatListRow = ChatConfirmedRow | ChatPendingRow;

export function isConfirmedRow(row: ChatListRow): row is ChatConfirmedRow {
  return row.kind === 'confirmed';
}

export function isPendingRow(row: ChatListRow): row is ChatPendingRow {
  return row.kind === 'pending';
}

export function toConfirmedRows(items: MessageResponse[]): ChatConfirmedRow[] {
  return items.map((message) => ({ kind: 'confirmed' as const, message }));
}
