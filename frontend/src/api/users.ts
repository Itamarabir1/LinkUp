import { api } from './client';
import type { PaginatedNotificationsResponse, User } from '../types/api';

export function fetchCurrentUser() {
  return api.get<User>('/users/me');
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

export function fetchMyNotifications(params?: { limit?: number; after?: string }) {
  return api.get<PaginatedNotificationsResponse>('/users/me/notifications', { params });
}

export function patchFcmToken(fcm_token: string | null) {
  return api.patch('/users/fcm-token', { fcm_token });
}
