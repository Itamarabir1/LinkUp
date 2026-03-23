import { useCallback, useEffect } from 'react';
import type { Dispatch } from 'react';
import { fetchUnreadMessageCount } from '../api/chat';
import type { ChatAction } from './chatState';

export function useChatUnreadMessages(userId: string | undefined, dispatch: Dispatch<ChatAction>) {
  const refreshUnread = useCallback(async () => {
    if (!userId) return;
    try {
      const { data } = await fetchUnreadMessageCount();
      dispatch({
        type: 'SET_UNREAD_MESSAGES',
        count: typeof data?.count === 'number' ? data.count : 0,
      });
    } catch {
      // ignore
    }
  }, [userId, dispatch]);

  useEffect(() => {
    if (!userId) return;
    void (async () => {
      await refreshUnread();
    })();
    const interval = setInterval(refreshUnread, 30000);
    return () => clearInterval(interval);
  }, [userId, refreshUnread]);

  return refreshUnread;
}
