import { api } from './client';
import type { User } from '../types/api';

export type RegisterPayload = {
  full_name: string;
  email: string;
  phone_number: string;
  password: string;
  confirm_password: string;
};

export function loginWithPassword(email: string, password: string) {
  return api.post<{ access_token: string; user: User }>('/auth/login', {
    email,
    password,
  });
}

export function registerUser(payload: RegisterPayload) {
  return api.post('/auth/register', payload);
}

export function signInWithGoogleToken(idToken: string) {
  return api.post<{ access_token: string; user: User }>(
    '/auth/google-signin',
    { id_token: idToken },
    { timeout: 60000 }
  );
}

export function logoutSession() {
  return api.post('/auth/logout');
}

export function verifyEmailCode(email: string, code: string) {
  return api.post('/auth/verify-email', { code, email });
}

export function resendVerificationEmail(email: string) {
  return api.post('/auth/resend-verification', { email });
}
