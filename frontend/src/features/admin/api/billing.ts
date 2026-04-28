import { api } from '../../../api/client';
import type { AdminPaginated } from './bookings';

export type AdminPaymentRow = {
  payment_id: string;
  user_id: string;
  amount: number;
  currency: string;
  status: string;
  stripe_payment_intent_id: string | null;
  stripe_session_id: string | null;
  stripe_event_id: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export function fetchAdminBillingPayments(params?: {
  status?: string;
  user_id?: string;
  currency?: string;
  limit?: number;
  offset?: number;
}) {
  return api.get<AdminPaginated<AdminPaymentRow>>('/admin/billing/payments', { params });
}
