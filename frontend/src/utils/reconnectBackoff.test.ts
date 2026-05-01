import { describe, expect, it } from 'vitest';
import {
  computeReconnectDelayMs,
  RECONNECT_BACKOFF_BASE_MS,
  RECONNECT_BACKOFF_MAX_MS,
} from './reconnectBackoff';

describe('computeReconnectDelayMs', () => {
  const neutralRandom = () => 0.5;

  it('doubles base with no jitter effect when random is 0.5', () => {
    const opts = { random: neutralRandom };
    expect(computeReconnectDelayMs(0, opts)).toBe(3000);
    expect(computeReconnectDelayMs(1, opts)).toBe(6000);
    expect(computeReconnectDelayMs(2, opts)).toBe(12_000);
    expect(computeReconnectDelayMs(3, opts)).toBe(24_000);
  });

  it('caps at maxMs', () => {
    const opts = { random: neutralRandom };
    expect(computeReconnectDelayMs(4, opts)).toBe(30_000);
    expect(computeReconnectDelayMs(10, opts)).toBe(30_000);
  });

  it('uses baseMs from options', () => {
    const opts = { baseMs: 1000, random: neutralRandom };
    expect(computeReconnectDelayMs(0, opts)).toBe(1000);
    expect(computeReconnectDelayMs(2, opts)).toBe(4000);
  });

  it('applies ±20% jitter at bounds (min at random=0, max at random≈1)', () => {
    const baseOpts = { jitterRatio: 0.2 };
    expect(computeReconnectDelayMs(0, { ...baseOpts, random: () => 0 })).toBe(Math.round(3000 * 0.8));
    expect(computeReconnectDelayMs(0, { ...baseOpts, random: () => 0.999999 })).toBe(
      Math.round(3000 * 1.2)
    );
    const capped = RECONNECT_BACKOFF_MAX_MS;
    expect(computeReconnectDelayMs(4, { ...baseOpts, random: () => 0 })).toBe(Math.round(capped * 0.8));
    expect(computeReconnectDelayMs(4, { ...baseOpts, random: () => 0.999999 })).toBe(
      Math.round(capped * 1.2)
    );
  });

  it('exports default constants', () => {
    expect(RECONNECT_BACKOFF_BASE_MS).toBe(3000);
    expect(RECONNECT_BACKOFF_MAX_MS).toBe(30_000);
  });
});
