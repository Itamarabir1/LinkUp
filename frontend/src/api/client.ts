import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { API_BASE_URL, API_TIMEOUT_MS, CHAT_WS_HTTP_BASE } from '../config/env';
import type { PaginatedMessagesResponse } from '../types/api';

// לוודא לאן הבקשות הולכות (יופיע בקונסול של הדפדפן F12)
console.log('[Linkup Frontend] API Base URL:', API_BASE_URL);

const TOKEN_KEY = 'linkup_access_token';
const REFRESH_KEY = 'linkup_refresh_token';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});

function getStoredAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getStoredRefreshToken();
  if (!refresh) return null;
  try {
    const { data } = await axios.post<{
      access_token: string;
      refresh_token: string;
    }>(`${API_BASE_URL}/auth/refresh`, { refresh_token: refresh }, {
      headers: { 'Content-Type': 'application/json' },
      timeout: API_TIMEOUT_MS,
    });
    const newAccess = data.access_token;
    const newRefresh = data.refresh_token;
    if (newAccess) {
      localStorage.setItem(TOKEN_KEY, newAccess);
      if (newRefresh) localStorage.setItem(REFRESH_KEY, newRefresh);
      return newAccess;
    }
  } catch {
    clearTokens();
  }
  return null;
}

let isRefreshing = false;
const failedQueue: Array<{
  resolve: (token: string | null) => void;
  reject: (err: AxiosError) => void;
}> = [];

function processQueue(error: AxiosError | null, token: string | null) {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token)));
  failedQueue.length = 0;
}

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getStoredAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }
    return config;
  },
  (err) => Promise.reject(err)
);

api.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original = err.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };
    if (err.response?.status !== 401 || original._retry) {
      return Promise.reject(err);
    }
    if (isRefreshing) {
      return new Promise<void>((resolve, reject) => {
        failedQueue.push({
          resolve: (t) => {
            if (t) original.headers.Authorization = `Bearer ${t}`;
            resolve();
          },
          reject,
        });
      }).then(() => api(original));
    }
    original._retry = true;
    isRefreshing = true;
    const newToken = await refreshAccessToken();
    isRefreshing = false;
    processQueue(null, newToken);
    if (newToken) {
      original.headers.Authorization = `Bearer ${newToken}`;
      return api(original);
    }
    processQueue(err, null);
    return Promise.reject(err);
  }
);

/** בקשות HTTP ל-chat-ws (presence) — לא ל-backend */
export const chatWsApi = axios.create({
  baseURL: CHAT_WS_HTTP_BASE,
  timeout: API_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});
chatWsApi.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getStoredAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Chat API helpers
export interface ConversationDetail {
  conversation_id: string;
  partner: {
    user_id: string;
    full_name: string;
    avatar_url?: string;
  };
  created_at: string;
  booking_id?: string;
}

export interface ConversationListItem {
  conversation_id: string;
  partner: { user_id: string; full_name: string; avatar_url?: string };
  last_message_at: string | null;
  last_message_preview: string | null;
}

export interface MessageResponse {
  message_id: number;
  conversation_id: string;
  sender_id: string;
  body: string;
  created_at: string;
}

/**
 * פותח שיחה עם נהג/נוסע דרך booking_id.
 * רק נהג או נוסע של ה-booking יכולים לפתוח שיחה.
 */
export async function openChatByBooking(bookingId: string): Promise<ConversationDetail> {
  const { data } = await api.post<ConversationDetail>(
    `/chat/conversations/by-booking/${bookingId}`
  );
  return data;
}

export function listConversations(): Promise<{ data: ConversationListItem[] }> {
  return api.get<ConversationListItem[]>('/chat/conversations');
}

export function getConversation(conversationId: string): Promise<{ data: ConversationDetail }> {
  return api.get<ConversationDetail>(`/chat/conversations/${conversationId}`);
}

export function getMessages(
  conversationId: string,
  params?: { limit?: number; before?: number }
): Promise<{ data: PaginatedMessagesResponse }> {
  return api.get<PaginatedMessagesResponse>(`/chat/conversations/${conversationId}/messages`, { params });
}

export function sendMessage(conversationId: string, body: string): Promise<{ data: MessageResponse }> {
  return api.post<MessageResponse>(`/chat/conversations/${conversationId}/messages`, { body });
}
