import { useEffect, useRef, useState, type MutableRefObject } from 'react';
import { APP_CONFIG } from '../../config/runtime';
import './googleIdentity';

/**
 * טוען את סקריפט Google Identity Services ומאתחל את google.accounts.id (פעם אחת).
 */
export function useGoogleSignInScript(
  onError: ((msg: string) => void) | undefined,
  credentialRef: MutableRefObject<((response: { credential: string }) => Promise<void>) | null>
): { scriptLoaded: boolean; initialized: boolean } {
  const [scriptLoaded, setScriptLoaded] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const initializedRef = useRef(false);

  useEffect(() => {
    const googleClientId = APP_CONFIG.google.clientId;
    if (!googleClientId) {
      console.error('VITE_GOOGLE_CLIENT_ID not set in environment variables');
      onError?.('Google Client ID לא מוגדר. אנא הגדר VITE_GOOGLE_CLIENT_ID ב-.env');
      return;
    }

    if (initialized || scriptLoaded) return;

    const initializeGoogleSignIn = () => {
      if (!window.google?.accounts?.id) {
        console.error('[GoogleSignIn] Google Identity Services API not available');
        return false;
      }

      if (initializedRef.current) {
        return true;
      }

      const currentOrigin = window.location.origin;

      try {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: async (response: { credential: string }) => {
            await credentialRef.current?.(response);
          },
          auto_select: false,
          cancel_on_tap_outside: true,
          itp_support: true,
        });
        initializedRef.current = true;
        setInitialized(true);
        return true;
      } catch (err) {
        console.error('[GoogleSignIn] ❌ Failed to initialize Google Identity Services:', err);
        const msg = err instanceof Error ? err.message : String(err);
        const isOriginError = /origin|not allowed|403|client id/i.test(msg);
        if (isOriginError && onError) {
          onError(
            `ה-origin לא מורשה ב-Google. Origin: ${currentOrigin}. Client ID: ${googleClientId}. הוסף בדיוק את ה-origin הזה ב-Google Cloud Console → Credentials → ה-Client ID → Authorized JavaScript origins.`
          );
        }
        if (err instanceof Error) {
          console.error('[GoogleSignIn] Error message:', err.message);
          console.error('[GoogleSignIn] Error stack:', err.stack);
        }
        return false;
      }
    };

    const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
    if (existingScript && window.google?.accounts?.id) {
      initializeGoogleSignIn();
      setScriptLoaded(true);
      return () => {
        setInitialized(false);
        setScriptLoaded(false);
        initializedRef.current = false;
      };
    }
    if (existingScript) {
      let checkCount = 0;
      const maxChecks = 50;
      const checkInterval = setInterval(() => {
        checkCount++;
        if (window.google?.accounts?.id) {
          clearInterval(checkInterval);
          initializeGoogleSignIn();
          setScriptLoaded(true);
        } else if (checkCount >= maxChecks) {
          clearInterval(checkInterval);
          console.error('Google Identity Services failed to load after timeout');
          onError?.('Google Sign-In לא נטען. אנא רענן את הדף.');
        }
      }, 100);
      return () => {
        clearInterval(checkInterval);
        setInitialized(false);
        setScriptLoaded(false);
        initializedRef.current = false;
      };
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      setTimeout(() => {
        if (window.google?.accounts?.id) {
          initializeGoogleSignIn();
          setScriptLoaded(true);
        } else {
          console.error('Google Identity Services API not available after script load');
          onError?.('Google Sign-In לא זמין. אנא רענן את הדף.');
        }
      }, 100);
    };
    script.onerror = () => {
      console.error('Failed to load Google Identity Services script (may be 403 - origin not allowed)');
      const origin = window.location.origin;
      onError?.(
        `טעינת Google Sign-In נכשלה. Origin: ${origin}. Client ID: ${googleClientId}. בדוק שה-origin מורשה עבור ה-Client ID הזה ב-Google Cloud Console → Credentials → Authorized JavaScript origins.`
      );
    };
    document.head.appendChild(script);

    return () => {
      setInitialized(false);
      setScriptLoaded(false);
      initializedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount once; state managed inside
  }, [onError, credentialRef]);

  return { scriptLoaded, initialized };
}
