import { useEffect, useRef } from 'react';

type UserEventDetail = {
  event?: string;
  ride_id?: string;
  booking_id?: string;
  request_id?: string;
  status?: string;
};

/**
 * Subscribe to a specific linkup:user-event by event name.
 * handler is stored in a ref — safe to pass inline lambdas.
 */
export function useUserEvent(
  eventName: string | string[],
  handler: (detail: UserEventDetail) => void
) {
  const handlerRef = useRef(handler);
  useEffect(() => {
    handlerRef.current = handler;
  });

  // Stable primitive key: inline array literals get a new reference every render and would re-subscribe the listener unnecessarily.
  const depsKey = Array.isArray(eventName)
    ? [...eventName].sort().join(',')
    : eventName;

  useEffect(() => {
    const names = Array.isArray(eventName) ? eventName : [eventName];
    const listener = (evt: Event) => {
      const detail = (evt as CustomEvent<UserEventDetail>).detail;
      if (!detail?.event) return;
      if (names.includes(detail.event)) {
        handlerRef.current(detail);
      }
    };
    window.addEventListener('linkup:user-event', listener);
    return () => window.removeEventListener('linkup:user-event', listener);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- depsKey mirrors eventName content; including eventName would defeat stabilization
  }, [depsKey]);
}
