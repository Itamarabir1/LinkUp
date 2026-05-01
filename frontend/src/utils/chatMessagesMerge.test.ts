import { describe, expect, it } from 'vitest';
import type { ChatListRow } from '../types/chatList';
import {
  appendMessageDedupById,
  applyInboundRealMessage,
  removePendingByClientId,
} from './chatMessagesMerge';

describe('appendMessageDedupById', () => {
  const m1 = {
    message_id: 1,
    conversation_id: 'c',
    sender_id: 'u',
    body: 'hi',
    created_at: 't',
  };

  it('appends when message_id is new', () => {
    expect(appendMessageDedupById([], m1)).toEqual([m1]);
    expect(
      appendMessageDedupById([m1], {
        ...m1,
        message_id: 2,
        body: 'there',
      })
    ).toEqual([m1, { ...m1, message_id: 2, body: 'there' }]);
  });

  it('returns same array reference when message_id exists', () => {
    const prev = [m1];
    expect(appendMessageDedupById(prev, { ...m1, body: 'changed' })).toBe(prev);
  });
});

describe('applyInboundRealMessage', () => {
  const m1 = {
    message_id: 1,
    conversation_id: 'c',
    sender_id: 'u',
    body: 'hi',
    created_at: 't1',
  };
  const pending = (clientId: string): ChatListRow => ({
    kind: 'pending',
    client_message_id: clientId,
    conversation_id: 'c',
    sender_id: 'u',
    body: 'out',
    created_at: 't0',
  });
  const confirmed = (m: typeof m1): ChatListRow => ({ kind: 'confirmed', message: m });

  it('drops pending by client id then appends real message', () => {
    const prev: ChatListRow[] = [confirmed(m1), pending('cid-1')];
    const real = { ...m1, message_id: 2, body: 'out', created_at: 't2' };
    expect(applyInboundRealMessage(prev, real, { dropPendingClientId: 'cid-1' })).toEqual([
      confirmed(m1),
      confirmed(real),
    ]);
  });

  it('WS-before-REST: pending removed; second apply dedupes by message_id', () => {
    const prev: ChatListRow[] = [confirmed(m1), pending('x')];
    const real = { ...m1, message_id: 2, body: 'x', created_at: 't2' };
    const once = applyInboundRealMessage(prev, real, { dropPendingClientId: 'x' });
    expect(once).toEqual([confirmed(m1), confirmed(real)]);
    const twice = applyInboundRealMessage(once, real, { dropPendingClientId: null });
    expect(twice).toEqual(once);
  });

  it('REST-before-WS: first call drops pending; second with null drop still dedupes', () => {
    const prev: ChatListRow[] = [confirmed(m1), pending('x')];
    const real = { ...m1, message_id: 2, body: 'x', created_at: 't2' };
    const afterRest = applyInboundRealMessage(prev, real, { dropPendingClientId: 'x' });
    const afterWs = applyInboundRealMessage(afterRest, real, { dropPendingClientId: null });
    expect(afterWs).toEqual([confirmed(m1), confirmed(real)]);
  });

  it('re-attaches unrelated pending at tail after append', () => {
    const pOther = { ...pending('other'), client_message_id: 'other' };
    const prev: ChatListRow[] = [confirmed(m1), pOther];
    const real = { ...m1, message_id: 2, body: 'new', created_at: 't2' };
    const out = applyInboundRealMessage(prev, real, { dropPendingClientId: 'cid-1' });
    expect(out).toEqual([confirmed(m1), confirmed(real), pOther]);
  });
});

describe('removePendingByClientId', () => {
  it('removes only matching pending row', () => {
    const rows: ChatListRow[] = [
      { kind: 'confirmed', message: { message_id: 1, conversation_id: 'c', sender_id: 'u', body: 'a', created_at: 't' } },
      {
        kind: 'pending',
        client_message_id: 'drop-me',
        conversation_id: 'c',
        sender_id: 'u',
        body: 'b',
        created_at: 't',
      },
    ];
    expect(removePendingByClientId(rows, 'drop-me')).toEqual([rows[0]]);
    expect(removePendingByClientId(rows, 'missing')).toEqual(rows);
  });
});
