import { WS_URLS } from '../config/wsUrls';
import { UserEventSchema, type UserEvent } from '../types/wsEvents';
import { useReconnectingWebSocket } from './useReconnectingWebSocket';

type UseUserEventStreamParams = {
  enabled?: boolean;
  onEvent: (event: UserEvent) => void;
};

export function useUserEventStream({ enabled = true, onEvent }: UseUserEventStreamParams) {
  useReconnectingWebSocket({
    buildUrl: (token) => WS_URLS.chat(token),
    enabled,
    onMessage: (ev) => {
      try {
        const parsed = UserEventSchema.safeParse(JSON.parse(String(ev.data)));
        if (!parsed.success) return;
        onEvent(parsed.data);
      } catch {
        /* ignore invalid messages from shared stream */
      }
    },
  });
}
