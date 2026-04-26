/**
 * Token-bucket throttle for axios requests.
 * Capacity: 10 tokens, refill rate: 10/sec.
 * Each request consumes 1 token. If empty, waits up to MAX_WAIT_MS then rejects.
 */

const CAPACITY = 10;
const REFILL_RATE_PER_MS = 10 / 1000; // 10 tokens per second
const MAX_WAIT_MS = 2000;

let tokens = CAPACITY;
let lastRefill = Date.now();

function refill(): void {
  const now = Date.now();
  const elapsed = now - lastRefill;
  tokens = Math.min(CAPACITY, tokens + elapsed * REFILL_RATE_PER_MS);
  lastRefill = now;
}

export async function throttle(): Promise<void> {
  refill();
  tokens -= 1;
  if (tokens >= 0) return;

  const msToWait = Math.ceil((-tokens) / REFILL_RATE_PER_MS);
  if (msToWait > MAX_WAIT_MS) {
    tokens += 1;
    const err = new Error('Too many requests - throttled');
    (err as { code?: string }).code = 'ERR_THROTTLED';
    throw err;
  }

  await new Promise<void>((resolve) => setTimeout(resolve, msToWait));
  refill();
}
