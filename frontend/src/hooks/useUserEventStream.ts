import { WS_URLS } from '../config/wsUrls';
import {
  InvalidateEventSchema,
  UserEventSchema,
  type InvalidateEvent,
  type UserEvent,
} from '../types/wsEvents';
import { useReconnectingWebSocket } from './useReconnectingWebSocket';

type UseUserEventStreamParams = {
  enabled?: boolean;
  onUserEvent: (event: UserEvent) => void;
  onInvalidate: (event: InvalidateEvent) => void;
};

export function useUserEventStream({
  enabled = true,
  onUserEvent,
  onInvalidate,
}: UseUserEventStreamParams) {
  useReconnectingWebSocket({
    buildUrl: (token) => WS_URLS.chat(token),
    enabled,
    onMessage: (ev) => {
      const chunks = String(ev.data).split('\n');
      for (const line of chunks) {
        if (!line.trim()) continue;
        try {
          const raw = JSON.parse(line);

          const invalidate = InvalidateEventSchema.safeParse(raw);
          if (invalidate.success) {
            onInvalidate(invalidate.data);
            continue;
          }

          const userEvent = UserEventSchema.safeParse(raw);
          if (userEvent.success) {
            onUserEvent(userEvent.data);
          }
        } catch {
          continue;
        }
      }
    },
  });
}
