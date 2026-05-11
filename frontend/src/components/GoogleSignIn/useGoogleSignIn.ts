import { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { APP_CONFIG } from '../../config/runtime';
import { useAuth } from '../../context/AuthContext';
import { getApiErrorMessage, isTimeoutOrAbortError } from '../../utils/apiError';
import i18n from '../../i18n';
import { useGoogleSignInScript } from './useGoogleSignInScript';

export interface UseGoogleSignInOptions {
  onError?: (error: string) => void;
  disabled?: boolean;
}

export function useGoogleSignIn({ onError, disabled }: UseGoogleSignInOptions) {
  const [loading, setLoading] = useState(false);
  const [fallback, setFallback] = useState(false);
  const { signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const buttonRef = useRef<HTMLDivElement>(null);
  const credentialRef = useRef<((response: { credential: string }) => Promise<void>) | null>(null);

  const { scriptLoaded, initialized } = useGoogleSignInScript(onError, credentialRef);
  const googleLocale = i18n.resolvedLanguage?.startsWith('en') ? 'en' : 'he';

  useEffect(() => {
    credentialRef.current = async (response: { credential: string }) => {
      setLoading(true);
      try {
        await signInWithGoogle(response.credential);
        const searchParams = new URLSearchParams(location.search);
        const fromQuery = searchParams.get('from');
        let target = '/choose-destination';
        if (fromQuery) {
          const decoded = decodeURIComponent(fromQuery);
          if (decoded.startsWith('/') && !decoded.startsWith('//')) {
            target = decoded;
          }
        }
        navigate(target, { replace: true });
      } catch (err: unknown) {
        if (isTimeoutOrAbortError(err)) {
          onError?.(i18n.t('auth:backend_timeout'));
          return;
        }
        const e = err as { message?: string };
        onError?.(getApiErrorMessage(err, e.message || i18n.t('auth:error_login_failed')));
      } finally {
        setLoading(false);
      }
    };
  }, [signInWithGoogle, navigate, location.search, onError]);

  useEffect(() => {
    if (!scriptLoaded || !initialized || !buttonRef.current || disabled) return;

    const googleClientId = APP_CONFIG.google.clientId;
    if (!googleClientId) return;

    const container = buttonRef.current;
    const currentOrigin = window.location.origin;

    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    try {
      window.google!.accounts.id.renderButton(container, {
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        width: 300,
        locale: googleLocale,
      });
      setFallback(false);
    } catch (renderErr) {
      console.error(
        '[GoogleSignIn] renderButton failed:',
        renderErr instanceof Error ? renderErr.message : renderErr
      );
      const renderMsg = renderErr instanceof Error ? renderErr.message : String(renderErr);
      const isOriginError = /origin|not allowed|403|client id/i.test(renderMsg);
      if (isOriginError) {
        onError?.(i18n.t('auth:error_origin_not_allowed', { origin: currentOrigin }));
      }
      setFallback(true);
    }
  }, [scriptLoaded, initialized, disabled, onError, googleLocale]);

  return {
    buttonRef,
    scriptLoaded,
    loading,
    disabled,
    fallback,
  };
}
