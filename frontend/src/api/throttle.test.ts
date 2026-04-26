import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

beforeEach(() => {
  vi.useFakeTimers();
  vi.resetModules();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('throttle', () => {
  it('allows up to 10 concurrent requests without waiting', async () => {
    const { throttle } = await import('./throttle');
    const promises = Array.from({ length: 10 }, () => throttle());
    await expect(Promise.all(promises)).resolves.toBeDefined();
  });

  it('waits and succeeds for short overflow', async () => {
    const { throttle } = await import('./throttle');
    const firstTen = Array.from({ length: 10 }, () => throttle());
    await Promise.all(firstTen);

    const eleventh = throttle();
    await vi.advanceTimersByTimeAsync(100);
    await expect(eleventh).resolves.toBeUndefined();
  });

  it('rejects when max wait exceeded', async () => {
    const { throttle } = await import('./throttle');
    const calls = Array.from({ length: 31 }, () => throttle());

    await expect(calls[30]).rejects.toThrow('throttled');
    await vi.advanceTimersByTimeAsync(2000);
    await Promise.allSettled(calls);
  });
});
