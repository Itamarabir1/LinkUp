import axios from 'axios';
import { isApiError } from './types';

/** Maps common API error_code values to Hebrew when the server message is missing. */
const CODE_MESSAGES: Record<string, string> = {
  VALIDATION_ERROR: 'שגיאת וולידציה בנתונים',
  DATABASE_CONFLICT: 'פעולה זו אינה אפשרית עקב נתונים קיימים',
  DATABASE_ERROR: 'אירעה שגיאה, אנא נסה שוב',
  UNAUTHORIZED: 'נדרשת התחברות',
  INVALID_TOKEN: 'אסימון לא תקף',
  RATE_LIMIT_EXCEEDED: 'יותר מדי בקשות, נסה שוב בעוד רגע',
  CHAT_ROOM_NOT_FOUND: 'השיחה לא נמצאה',
  CHAT_UNAUTHORIZED_ACCESS: 'אין הרשאה לשיחה זו',
  CHAT_MESSAGE_SEND_FAILED: 'שליחת ההודעה נכשלה',
};

export function useErrorHandler() {
  function handleError(err: unknown): string {
    if (axios.isAxiosError(err) && err.response == null) {
      return 'בעיית חיבור לאינטרנט';
    }

    if (isApiError(err)) {
      const status = err.response.status;
      const data = err.response.data;
      if (status >= 500) {
        return 'אירעה שגיאה, אנא נסה שוב';
      }
      if (typeof data.message === 'string' && data.message.trim()) {
        return data.message;
      }
      const byCode = CODE_MESSAGES[data.error_code];
      if (byCode) return byCode;
      if (status >= 400 && status < 500) {
        return 'הבקשה לא הושלמה';
      }
    }

    if (err instanceof Error && err.message) {
      return err.message;
    }

    return 'אירעה שגיאה, אנא נסה שוב';
  }

  return { handleError };
}
