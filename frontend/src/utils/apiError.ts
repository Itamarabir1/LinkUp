/**
 * Normalizes Axios-like error shapes (FastAPI detail / custom message).
 */
export function getApiErrorMessage(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: unknown } })?.response?.data as
    | { detail?: unknown; message?: unknown }
    | undefined;
  if (!data) {
    return err instanceof Error && err.message ? err.message : fallback;
  }
  const raw = data.message ?? data.detail;
  if (typeof raw === 'string') return raw;
  if (Array.isArray(raw) && raw.length > 0) {
    const first = raw[0];
    if (typeof first === 'object' && first !== null && 'msg' in first) {
      return String((first as { msg: string }).msg);
    }
    return JSON.stringify(raw);
  }
  if (raw != null && typeof raw === 'object') return JSON.stringify(raw);
  return fallback;
}

export function getApiStatus(err: unknown): number | undefined {
  return (err as { response?: { status?: number } })?.response?.status;
}

export function getApiErrorCode(err: unknown): string | undefined {
  const data = (err as { response?: { data?: { error_code?: string } } })?.response?.data;
  return typeof data?.error_code === 'string' ? data.error_code : undefined;
}

export function getRegisterErrorMessage(err: unknown, t: (key: string) => string): string {
  const code = getApiErrorCode(err);
  if (code === 'USER_EMAIL_TAKEN') return t('error_email_taken');
  if (code === 'USER_PHONE_TAKEN') return t('error_phone_taken');

  if (code === 'VALIDATION_ERROR') {
    const details = (err as { response?: { data?: { details?: { fields?: Array<{ field?: string }> } } } })?.response
      ?.data?.details;
    const fields = Array.isArray(details?.fields) ? details.fields : [];
    const normalizedFields = fields
      .map((f) => (typeof f?.field === 'string' ? f.field.split('.').pop() : ''))
      .filter(Boolean);

    if (normalizedFields.includes('email')) return t('error_email_invalid');
    if (normalizedFields.includes('phone_number')) return t('error_phone_invalid');
    if (normalizedFields.includes('password')) return t('error_password_weak');
  }

  return getApiErrorMessage(err, t('error_register_failed'));
}

/** Axios timeout/abort detector for dedicated timeout handling paths. */
export function isTimeoutOrAbortError(err: unknown): boolean {
  const ax = err as { code?: string; message?: string };
  if (ax.code === 'ECONNABORTED') return true;
  if (typeof ax.message === 'string' && /timeout/i.test(ax.message)) return true;
  return false;
}
