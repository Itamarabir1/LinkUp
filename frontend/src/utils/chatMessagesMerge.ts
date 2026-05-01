import type { MessageResponse } from '../types/api';
import type { ChatListRow } from '../types/chatList';
import { isConfirmedRow, isPendingRow } from '../types/chatList';

/** Appends msg only if message_id is not already present (REST + WS single source). */
export function appendMessageDedupById(prev: MessageResponse[], msg: MessageResponse): MessageResponse[] {
  if (prev.some((existing) => existing.message_id === msg.message_id)) return prev;
  return [...prev, msg];
}

/** Removes a pending outbound row by client id (rollback). */
export function removePendingByClientId(prev: ChatListRow[], clientId: string): ChatListRow[] {
  return prev.filter((r) => !(isPendingRow(r) && r.client_message_id === clientId));
}

/**
 * Applies a server message to the chat list: optionally drops a correlated pending row,
 * dedupes/appends the real message, then re-attaches remaining pending rows at the tail.
 */
export function applyInboundRealMessage(
  prev: ChatListRow[],
  msg: MessageResponse,
  opts: { dropPendingClientId: string | null }
): ChatListRow[] {
  const afterDrop = opts.dropPendingClientId
    ? prev.filter(
        (r) => !(isPendingRow(r) && r.client_message_id === opts.dropPendingClientId)
      )
    : prev;

  const reals: MessageResponse[] = [];
  const pendings: ChatListRow[] = [];
  for (const r of afterDrop) {
    if (isConfirmedRow(r)) {
      reals.push(r.message);
    } else {
      pendings.push(r);
    }
  }

  const realsNext = appendMessageDedupById(reals, msg);
  const confirmedRows: ChatListRow[] = realsNext.map((m) => ({ kind: 'confirmed', message: m }));
  return [...confirmedRows, ...pendings];
}
