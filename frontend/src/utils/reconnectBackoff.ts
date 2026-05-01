/** Default WebSocket reconnect: first delay ~3s (before jitter), doubles, caps at 30s. */
export const RECONNECT_BACKOFF_BASE_MS = 3000;
export const RECONNECT_BACKOFF_MAX_MS = 30_000;
export const RECONNECT_BACKOFF_JITTER_RATIO = 0.2;

export interface ComputeReconnectDelayMsOptions {
  baseMs?: number;
  maxMs?: number;
  /** Fraction in [0,1]; delay multiplier in [1 - jitter, 1 + jitter]. Default 0.2 (= ±20%). */
  jitterRatio?: number;
  /** For tests; default `Math.random` in [0, 1). */
  random?: () => number;
}

function safeExponent(attemptIndex: number): number {
  if (!Number.isFinite(attemptIndex)) return 0;
  return Math.max(0, Math.floor(attemptIndex));
}

/**
 * Computes a single reconnect delay: exponential backoff from `baseMs`, capped at `maxMs`, then ±jitter on the capped value.
 */
export function computeReconnectDelayMs(
  attemptIndex: number,
  options: ComputeReconnectDelayMsOptions = {}
): number {
  const baseMs = options.baseMs ?? RECONNECT_BACKOFF_BASE_MS;
  const maxMs = options.maxMs ?? RECONNECT_BACKOFF_MAX_MS;
  const jitterRatio = options.jitterRatio ?? RECONNECT_BACKOFF_JITTER_RATIO;
  const random = options.random ?? Math.random;

  const exp = safeExponent(attemptIndex);
  const raw = baseMs * 2 ** exp;
  const capped = Math.min(raw, maxMs);
  const u = random();
  const jitterFactor = 1 + (u * 2 - 1) * jitterRatio;
  return Math.max(0, Math.round(capped * jitterFactor));
}
