import { api } from './client';

export interface BillingStatus {
  is_premium: boolean;
  premium_since: string | null;
}

export interface CheckoutSession {
  checkout_url: string;
  session_id: string;
}

export async function getBillingStatus(): Promise<BillingStatus> {
  const { data } = await api.get<BillingStatus>('/billing/status');
  return data;
}

export async function createCheckoutSession(): Promise<CheckoutSession> {
  const { data } = await api.post<CheckoutSession>('/billing/checkout');
  return data;
}
