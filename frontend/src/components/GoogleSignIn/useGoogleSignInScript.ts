import { useEffect, useState, type MutableRefObject } from 'react';
import { APP_CONFIG } from '../../config/runtime';
import { ensureGisInitialized, setGisCredentialHandler } from './gisLoader';

/**
 * Thin React adapter over the GIS module-level singleton ([gisLoader.ts](./gisLoader.ts)).
 *
 * - Subscribes the active credential handler to the singleton.
 * - Awaits the (idempotent) script-load + init.
 * - Surfaces a clean error to the caller's `onError` if init fails (origin
 *   not allowlisted, network blocked, etc.) with actionable next steps.
 *
 * The cleanup intentionally does NOT reset the singleton: GIS is initialized
 * once per page load, full stop. This is what makes the hook StrictMode-safe.
 */
export function useGoogleSignInScript(
  onError: ((msg: string) => void) | undefined,
  credentialRef: MutableRefObject<((response: { credential: string }) => Promise<void>) | null>
): { scriptLoaded: boolean; initialized: boolean } {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const clientId = APP_CONFIG.google.clientId;
    if (!clientId) {
      onError?.('Google Client ID לא מוגדר. אנא הגדר VITE_GOOGLE_CLIENT_ID ב-.env');
      return;
    }
    setGisCredentialHandler((response) => {
      void credentialRef.current?.(response);
    });
    ensureGisInitialized(clientId)
      .then(() => {
        if (!cancelled) setReady(true);
      })
      .catch((err: unknown) => {
        const origin = window.location.origin;
        const msg = err instanceof Error ? err.message : String(err);
        const isOriginErr = /origin|not allowed|403|client id|failed to load/i.test(msg);
        if (isOriginErr) {
          onError?.(
            `טעינת Google Sign-In נכשלה. Origin: ${origin}. Client ID: ${clientId.slice(0, 12)}…\n` +
              `ודא: (1) ה-origin הזה מופיע ב-Google Cloud Console → Credentials → Authorized JavaScript origins ` +
              `עבור ה-Client ID הזה, (2) אין רווחים/scheme שונה ב-Console, (3) אם הוספת לאחרונה — חכה 10 דקות לרענון cache.`
          );
        } else {
          onError?.(`Google Sign-In נכשל: ${msg}`);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [onError, credentialRef]);

  return { scriptLoaded: ready, initialized: ready };
}
