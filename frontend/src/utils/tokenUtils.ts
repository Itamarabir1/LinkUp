const EXPIRY_BUFFER_MS = 60_000;

/**
 * Decode JWT payload without crypto verification (signature was already
 * verified server-side).  Returns `null` for malformed tokens.
 */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split('.')[1];
    if (!base64) return null;
    return JSON.parse(atob(base64)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * `true` when the token is expired **or** will expire within
 * `EXPIRY_BUFFER_MS` (60 s).  Also returns `true` for unparseable tokens.
 */
export function isTokenExpiredOrNearExpiry(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== 'number') return true;
  return payload.exp * 1000 - Date.now() < EXPIRY_BUFFER_MS;
}
