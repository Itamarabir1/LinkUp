import { chatWsApi } from './client';

export type PartnerPresence = {
  online: boolean;
  last_seen: string | null;
};

export function fetchPartnerPresence(partnerId: string) {
  return chatWsApi.get<PartnerPresence>(`/presence/${partnerId}`);
}
