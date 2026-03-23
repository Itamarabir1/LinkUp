import { useCallback } from 'react';
import type { Dispatch } from 'react';
import type { ChatAction } from './chatState';

/** פתיחת צ'אט בפופאפ או בפנל לפי הנתיב הנוכחי */
export function useChatOpenClose(pathname: string, dispatch: Dispatch<ChatAction>) {
  const openChat = useCallback(
    (conversationId: string) => {
      if (pathname === '/messages') {
        dispatch({ type: 'OPEN_PANEL', conversationId });
      } else {
        dispatch({ type: 'OPEN_POPUP', conversationId });
      }
    },
    [pathname, dispatch]
  );

  const closeChat = useCallback(() => {
    dispatch({ type: 'CLOSE_ALL_CHATS' });
  }, [dispatch]);

  return { openChat, closeChat };
}
