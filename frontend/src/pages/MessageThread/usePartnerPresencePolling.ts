import { useEffect, type Dispatch, type SetStateAction } from 'react';
import { fetchPartnerPresence, type PartnerPresence } from '../../api/presence';

export type { PartnerPresence };

/** Polls chat-ws presence for the conversation partner. */
export function usePartnerPresencePolling(
  partnerId: string | undefined,
  setPresence: Dispatch<SetStateAction<PartnerPresence | null>>
) {
  useEffect(() => {
    if (!partnerId) return;
    let cancelled = false;
    const run = async () => {
      try {
        const { data } = await fetchPartnerPresence(partnerId);
        if (!cancelled) setPresence(data);
      } catch {
        // ignore
      }
    };
    void run();
    const interval = setInterval(run, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [partnerId, setPresence]);
}
