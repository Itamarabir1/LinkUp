import { useEffect } from 'react';

const APP_NAME = 'LinkUp';

/**
 * Sets `document.title` to a route-specific page title and restores the
 * previous title on unmount. Pass an i18n-translated string in.
 *
 * Pairs with the page-level `<h1>` (visible or `sr-only`) to give screen
 * readers and tab managers a meaningful page name. Avoid generic values
 * like the app name alone — that's already in the static `<title>` tag.
 */
export function usePageTitle(pageTitle: string | undefined): void {
  useEffect(() => {
    const previous = document.title;
    document.title = pageTitle ? `${pageTitle} · ${APP_NAME}` : APP_NAME;
    return () => {
      document.title = previous;
    };
  }, [pageTitle]);
}
