import { useEffect } from 'react';
import { getChatWebSocketUrl } from '../config/env';
import { UserEventSchema, type UserEvent } from '../types/wsEvents';

type UseUserEventStreamParams = {
  enabled?: boolean;
  onEvent: (event: UserEvent) => void;
};

export function useUserEventStream({ enabled = true, onEvent }: UseUserEventStreamParams) {
  useEffect(() => {
    if (!enabled) return;
    const token = localStorage.getItem('linkup_access_token');
    if (!token) return;

    const ws = new WebSocket(getChatWebSocketUrl(token));
    ws.onmessage = (ev) => {
      try {
        const parsed = UserEventSchema.safeParse(JSON.parse(String(ev.data)));
        if (!parsed.success) return;
        onEvent(parsed.data);
      } catch {
        // ignore invalid messages from shared stream
      }
    };

    return () => ws.close();
  }, [enabled, onEvent]);
}
