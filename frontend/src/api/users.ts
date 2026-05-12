import { api } from './client';
import type { PaginatedNotificationsResponse, User } from '../types/api';

export function fetchCurrentUser(opts?: { signal?: AbortSignal }) {
  return api.get<User>('/users/me', { signal: opts?.signal });
}

export function getAvatarUploadUrl() {
  return api.get<{ upload_url: string; staging_key: string }>('/users/me/avatar/upload-url');
}

export function confirmAvatar(staging_key: string) {
  return api.post('/users/me/avatar/confirm', { staging_key });
}

export function deleteMyAvatar() {
  return api.delete('/users/me/avatar');
}

export function fetchMyNotifications(params?: { limit?: number; after?: string; signal?: AbortSignal }) {
  const { signal, ...rest } = params ?? {};
  return api.get<PaginatedNotificationsResponse>('/users/me/notifications', { params: rest, signal });
}

export function markNotificationsReadApi(items: Array<{ booking_id: string; created_at: string }>) {
  return api.patch('/users/me/notifications/read', { items });
}

export function markAllNotificationsReadApi() {
  return api.patch('/users/me/notifications/read-all');
}

export function patchFcmToken(fcm_token: string | null) {
  return api.patch('/users/fcm-token', { fcm_token });
}
