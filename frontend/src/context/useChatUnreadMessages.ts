import { useCallback, useEffect } from 'react';
import type { Dispatch } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchUnreadMessageCount } from '../api/chat';
import { qk } from '../api/queryKeys';
import type { ChatAction } from './chatState';

export function useChatUnreadMessages(userId: string | undefined, dispatch: Dispatch<ChatAction>) {
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: qk.chat.unread(),
    queryFn: async () => {
      const { data } = await fetchUnreadMessageCount();
      return typeof data?.count === 'number' ? data.count : 0;
    },
    enabled: !!userId,
    staleTime: 0,
    refetchInterval: 30_000,
    refetchOnReconnect: false,
  });

  useEffect(() => {
    if (data === undefined) return;
    dispatch({ type: 'SET_UNREAD_MESSAGES', count: data });
  }, [data, dispatch]);

  useEffect(() => {
    if (userId) return;
    queryClient.removeQueries({ queryKey: qk.chat.unread() });
  }, [userId, queryClient]);

  const setUnreadDirect = useCallback(
    (count: number) => {
      if (!userId) return;
      queryClient.setQueryData(qk.chat.unread(), count);
    },
    [queryClient, userId]
  );

  const refreshUnread = useCallback(() => {
    if (!userId) return;
    void queryClient.invalidateQueries({ queryKey: qk.chat.unread() });
  }, [queryClient, userId]);

  return { refreshUnread, setUnreadDirect };
}
