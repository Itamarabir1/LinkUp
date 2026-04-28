import { useEffect, useRef } from 'react';
import { useIsFetching } from '@tanstack/react-query';

const DEFAULT_FAVICON = '/favicon.svg';
const LOADING_FAVICON = '/favicon-loading.svg';

export function useFaviconLoader(): void {
  const isFetching = useIsFetching();
  const originalHrefRef = useRef<string | null>(null);
  const linkRef = useRef<HTMLLinkElement | null>(null);
  const createdLinkRef = useRef(false);

  useEffect(() => {
    let faviconLink = document.querySelector<HTMLLinkElement>("link[rel~='icon']");
    if (!faviconLink) {
      faviconLink = document.createElement('link');
      faviconLink.rel = 'icon';
      document.head.appendChild(faviconLink);
      createdLinkRef.current = true;
    }

    if (originalHrefRef.current == null) {
      originalHrefRef.current = faviconLink.getAttribute('href') ?? DEFAULT_FAVICON;
    }
    linkRef.current = faviconLink;
  }, []);

  useEffect(() => {
    if (!linkRef.current) return;
    linkRef.current.setAttribute('href', isFetching > 0 ? LOADING_FAVICON : DEFAULT_FAVICON);
  }, [isFetching]);

  useEffect(() => {
    return () => {
      if (createdLinkRef.current) {
        linkRef.current?.remove();
      } else if (linkRef.current && originalHrefRef.current) {
        linkRef.current.setAttribute('href', originalHrefRef.current);
      }
    };
  }, []);
}
