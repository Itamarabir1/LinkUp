import type { MutableRefObject } from 'react';

export function consumeOrCreateKey(ref: MutableRefObject<string | null>): string {
  if (ref.current === null) {
    ref.current = crypto.randomUUID();
  }
  return ref.current;
}

export function resetOutboundKey(ref: MutableRefObject<string | null>): void {
  ref.current = null;
}
