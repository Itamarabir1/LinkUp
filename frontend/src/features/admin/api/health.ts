import { api } from '../../../api/client';

export type AdminHealthResponse = {
  database: 'ok' | 'error';
  redis: 'ok' | 'error';
  rabbitmq: 'ok' | 'error';
  status: 'healthy' | 'unhealthy';
};

export function fetchAdminHealth() {
  return api.get<AdminHealthResponse>('/admin/health');
}
