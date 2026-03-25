import { api } from '../../../api/client';

export type AdminOutboxRow = {
  id: string;
  event_name: string;
  status: string;
  retry_count: number;
  created_at: string | null;
  processed_at: string | null;
};

export type AdminOutboxDetail = {
  id: string;
  event_name: string;
  status: string;
  retry_count: number;
  last_error: string | null;
  targets: string[];
  payload: unknown;
  metadata: unknown;
  created_at: string | null;
  processed_at: string | null;
};

export function fetchAdminOutbox(params?: {
  status?: string;
  event_name?: string;
  limit?: number;
}) {
  return api.get<AdminOutboxRow[]>('/admin/outbox', { params });
}

export function fetchAdminOutboxById(event_id: string) {
  return api.get<AdminOutboxDetail>(`/admin/outbox/${event_id}`);
}
