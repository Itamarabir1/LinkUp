import { useCallback, useEffect, useState } from 'react';

type Status = 'loading' | 'ready' | 'error';

export interface AdminFetchState<T> {
  status: Status;
  data: T | null;
  reload: () => void;
}

export function useAdminFetch<T>(
  fetcher: () => Promise<{ data: T }>
): AdminFetchState<T> {
  const [status, setStatus] = useState<Status>('loading');
  const [data, setData] = useState<T | null>(null);

  const load = useCallback(async () => {
    setStatus('loading');
    try {
      const res = await fetcher();
      setData(res.data);
      setStatus('ready');
    } catch {
      setStatus('error');
    }
  }, [fetcher]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus('loading');
      try {
        const res = await fetcher();
        if (!cancelled) {
          setData(res.data);
          setStatus('ready');
        }
      } catch {
        if (!cancelled) setStatus('error');
      }
    })();
    return () => { cancelled = true; };
  }, [fetcher]);

  return { status, data, reload: load };
}
