// בפיתוח: URL יחסי כדי שהבקשות יעברו דרך Vite proxy (ללא CORS). בפרודקשן: VITE_API_URL או fallback
const API_BASE_URL = import.meta.env.DEV
  ? '/api/v1'
  : (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1');

const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

// timeout לבקשות API (מילישניות). ברירת מחדל 30 שניות – מונע timeout בהתחלה איטית של השרת
const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS) || 30000;

// WebSocket URL for real-time chat and typing (chat-ws). In dev often ws://localhost:8081
const CHAT_WS_URL =
  import.meta.env.VITE_CHAT_WS_URL ||
  (import.meta.env.DEV ? 'ws://localhost:8081' : 'ws://127.0.0.1:8081');

/** HTTP base של chat-ws (presence וכו'). אופציונלי: VITE_CHAT_HTTP_URL */
function chatWsUrlToHttpBase(wsUrl: string): string {
  const s = wsUrl.trim();
  const withProto = s.startsWith('ws') ? s : `ws://${s}`;
  try {
    const u = new URL(withProto);
    const protocol = u.protocol === 'wss:' ? 'https:' : 'http:';
    return `${protocol}//${u.host}`;
  } catch {
    return (
      s.replace(/^wss:\/\//i, 'https://').replace(/^ws:\/\//i, 'http://').split('/')[0] ||
      'http://127.0.0.1:8081'
    );
  }
}
const CHAT_WS_HTTP_BASE =
  (import.meta.env.VITE_CHAT_HTTP_URL as string | undefined)?.replace(/\/$/, '') ||
  chatWsUrlToHttpBase(CHAT_WS_URL);

export function getWsBaseUrl(): string {
  if (import.meta.env.DEV) {
    return 'ws://localhost:8000/api/v1';
  }
  const protocol =
    typeof window !== 'undefined' && window.location.protocol === 'https:'
      ? 'wss:'
      : 'ws:';
  const host = typeof window !== 'undefined' ? window.location.host : '';
  return `${protocol}//${host}/api/v1`;
}

export { API_BASE_URL, GOOGLE_MAPS_API_KEY, API_TIMEOUT_MS, CHAT_WS_URL, CHAT_WS_HTTP_BASE };
