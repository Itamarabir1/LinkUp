import { createRef } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { MessageThreadViewModel } from './useMessageThread';
import MessageThreadPanel from './MessageThreadPanel';
import styles from './MessageThread.module.css';

vi.mock('react-i18next', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-i18next')>();
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string, params?: Record<string, string>) => {
        if (key === 'msg_typing') return `${params?.name ?? ''} is typing...`;
        const map: Record<string, string> = {
          msg_thread_loading: 'Loading conversation...',
          msg_back_to_messages: 'Back to messages',
          msg_conversation_fallback: 'Chat',
          msg_online: 'Online',
          msg_last_seen: 'Last seen',
          msg_load_older: 'Load older messages',
          msg_empty_thread: 'No messages yet. Send the first one.',
          msg_compose_placeholder: 'Write a message...',
          msg_send: 'Send',
          msg_back_aria: 'Back',
          msg_read: 'Read',
          msg_sent: 'Sent',
          loading: 'Loading',
        };
        return map[key] ?? key;
      },
    }),
  };
});

function makeVm(overrides: Partial<MessageThreadViewModel> = {}): MessageThreadViewModel {
  return {
    cid: 'conv-1',
    user: { user_id: 'u-me', email: 'me@test.dev' },
    conversation: {
      conversation_id: 'conv-1',
      created_at: '2024-01-01T00:00:00Z',
      partner: { user_id: 'u-partner', full_name: 'Partner' },
      partner_read_up_to_message_id: 2,
    },
    messages: [
      {
        kind: 'confirmed',
        message: {
          message_id: 1,
          conversation_id: 'conv-1',
          sender_id: 'u-me',
          body: 'first',
          created_at: '2024-01-01T10:00:00Z',
        },
      },
      {
        kind: 'confirmed',
        message: {
          message_id: 2,
          conversation_id: 'conv-1',
          sender_id: 'u-me',
          body: 'second',
          created_at: '2024-01-01T10:01:00Z',
        },
      },
      {
        kind: 'confirmed',
        message: {
          message_id: 3,
          conversation_id: 'conv-1',
          sender_id: 'u-me',
          body: 'third',
          created_at: '2024-01-01T10:02:00Z',
        },
      },
    ],
    messagesHasMore: false,
    loading: false,
    loadingMore: false,
    sending: false,
    error: '',
    input: '',
    partnerTyping: false,
    partnerTypingName: null,
    partnerPresence: null,
    partnerReadUpToId: 2,
    messagesEndRef: createRef<HTMLDivElement>(),
    loadMoreMessages: vi.fn(async () => {}),
    handleSend: vi.fn(async () => {}),
    onInputChange: vi.fn(),
    ...overrides,
  };
}

describe('MessageThreadPanel', () => {
  it('shows read receipts on all outgoing messages and colors only those up to the cursor', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <MessageThreadPanel vm={makeVm()} />
      </MemoryRouter>
    );

    expect(html.match(/aria-label="(Read|Sent)"/g)).toHaveLength(3);
    expect(html.split(styles.readReceiptRead).length - 1).toBe(2);
    expect(html.split(styles.readReceiptSent).length - 1).toBe(1);
  });

  it('renders empty thread without read receipts', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <MessageThreadPanel
          vm={makeVm({
            messages: [],
            partnerReadUpToId: null,
          })}
        />
      </MemoryRouter>
    );

    expect(html).toContain('No messages yet. Send the first one.');
    expect(html).not.toContain(styles.readReceipt);
  });

  it('renders pending outbound row with busy state and spinner, without read receipt', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <MessageThreadPanel
          vm={makeVm({
            messages: [
              {
                kind: 'confirmed',
                message: {
                  message_id: 1,
                  conversation_id: 'conv-1',
                  sender_id: 'u-me',
                  body: 'first',
                  created_at: '2024-01-01T10:00:00Z',
                },
              },
              {
                kind: 'pending',
                client_message_id: 'pending-cid-1',
                conversation_id: 'conv-1',
                sender_id: 'u-me',
                body: 'sending…',
                created_at: '2024-01-01T10:05:00Z',
              },
            ],
            partnerReadUpToId: 5,
          })}
        />
      </MemoryRouter>
    );

    expect(html).toContain('aria-busy="true"');
    expect(html).toContain(styles.msgPending);
    expect(html).toContain(styles.msgPendingSpinner);
    expect(html.match(/aria-label="(Read|Sent)"/g)).toHaveLength(1);
  });
});
