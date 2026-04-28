import { api } from '../../../api/client';

export type AdminSystemOverview = {
  health: Record<string, unknown>;
  outbox: { pending: number; failed: number };
  billing: { pending: number; failed: number };
  rabbitmq_clients: { api: boolean; worker: boolean; outbox: boolean };
};

export type AdminQueueRow = {
  queue_name: string;
  exchange_names: string[];
  retry_enabled: boolean;
  retry_delay_ms: number;
  max_retries: number;
  prefetch_count: number;
  durable: boolean;
};

export type AdminQueuesResponse = {
  queues: AdminQueueRow[];
  outbox_depth: { pending: number; failed: number };
};

export type AdminWorkersResponse = {
  workers: Array<{
    name: string;
    metrics_port: number;
    rabbitmq_client_connected: boolean;
  }>;
};

export function fetchAdminSystemOverview() {
  return api.get<AdminSystemOverview>('/admin/system/overview');
}

export function fetchAdminQueues() {
  return api.get<AdminQueuesResponse>('/admin/queues');
}

export function fetchAdminWorkers() {
  return api.get<AdminWorkersResponse>('/admin/workers');
}
