import { chatWsApi } from './client';

export type PartnerPresence = {
  online: boolean;
  last_seen: string | null;
};

export function fetchPartnerPresence(partnerId: string, opts?: { signal?: AbortSignal }) {
  return chatWsApi.get<PartnerPresence>(`/presence/${partnerId}`, { signal: opts?.signal });
}
