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
      const chunks = String(ev.data).split('\n');
      for (const line of chunks) {
        if (!line.trim()) continue;
        try {
          const parsed = UserEventSchema.safeParse(JSON.parse(line));
          if (!parsed.success) continue;
          onEvent(parsed.data);
        } catch {
          continue;
        }
      }
    },
  });
}
