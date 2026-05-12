import { useCallback, useEffect, useRef } from 'react';

/**
 * Returns a `getSignal()` function that:
 *  1. Aborts any previously issued signal (cancels the old in-flight request)
 *  2. Creates and returns a fresh AbortSignal
 *  3. Auto-aborts on component unmount
 */
export function useAbortSignal() {
  const controllerRef = useRef<AbortController | null>(null);

  const getSignal = useCallback((): AbortSignal => {
    controllerRef.current?.abort();
    controllerRef.current = new AbortController();
    return controllerRef.current.signal;
  }, []);

  useEffect(() => {
    return () => controllerRef.current?.abort();
  }, []);

  return getSignal;
}
