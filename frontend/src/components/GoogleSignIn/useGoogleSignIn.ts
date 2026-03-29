import { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ERROR_MESSAGES } from '../../config/constants';
import { useAuth } from '../../context/AuthContext';
import { getApiErrorMessage } from '../../utils/apiError';
import { useGoogleSignInScript } from './useGoogleSignInScript';

export interface UseGoogleSignInOptions {
  onError?: (error: string) => void;
  disabled?: boolean;
}

export function useGoogleSignIn({ onError, disabled }: UseGoogleSignInOptions) {
  const [loading, setLoading] = useState(false);
  const { signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const buttonRef = useRef<HTMLDivElement>(null);
  const credentialRef = useRef<((response: { credential: string }) => Promise<void>) | null>(null);

  const { scriptLoaded, initialized } = useGoogleSignInScript(onError, credentialRef);

  useEffect(() => {
    credentialRef.current = async (response: { credential: string }) => {
      setLoading(true);
      try {
        await signInWithGoogle(response.credential);
        const searchParams = new URLSearchParams(location.search);
        const fromQuery = searchParams.get('from');
        if (fromQuery) {
          navigate(decodeURIComponent(fromQuery), { replace: true });
        } else {
          navigate('/choose-destination', { replace: true });
        }
      } catch (err: unknown) {
        const e = err as { code?: string; message?: string };
        if ((e.code === 'ECONNABORTED' || (e.message && e.message.includes('timeout'))) && onError) {
          onError(ERROR_MESSAGES.BACKEND_TIMEOUT);
          return;
        }
        onError?.(getApiErrorMessage(err, e.message || 'התחברות נכשלה'));
      } finally {
        setLoading(false);
      }
    };
  }, [signInWithGoogle, navigate, location.search, onError]);

  useEffect(() => {
    if (!scriptLoaded || !initialized || !buttonRef.current || disabled) return;

    const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!googleClientId) return;

    try {
      if (buttonRef.current) {
        const currentOrigin = window.location.origin;

        buttonRef.current.innerHTML = '';

        try {
          try {
            window.google!.accounts.id.renderButton(buttonRef.current, {
              theme: 'outline',
              size: 'large',
              text: 'signin_with',
              width: 300,
            });
          } catch (renderErr) {
            console.error(
              '[GoogleSignIn] renderButton failed, using fallback:',
              renderErr instanceof Error ? renderErr.message : renderErr
            );
            const renderMsg = renderErr instanceof Error ? renderErr.message : String(renderErr);
            const isOriginError = /origin|not allowed|403|client id/i.test(renderMsg);
            if (isOriginError && onError) {
              onError(
                `ה-origin לא מורשה ב-Google. הוסף בדיוק את הכתובת הזו ב-Google Cloud Console → Credentials → ה-Client ID → Authorized JavaScript origins: ${currentOrigin}`
              );
            }
            if (buttonRef.current) {
              buttonRef.current.innerHTML = `
                <button 
                  id="google-signin-button" 
                  style="
                    width: 100%;
                    padding: 0.75rem 1rem;
                    font-size: 1rem;
                    font-weight: 500;
                    border: 1px solid #d1d5db;
                    border-radius: 0.5rem;
                    background-color: #fff;
                    color: #374151;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.5rem;
                  "
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  התחבר עם Google
                </button>
              `;

              const manualButton = buttonRef.current.querySelector('#google-signin-button');
              if (manualButton) {
                manualButton.addEventListener('click', () => {
                  window.google!.accounts.id.prompt((notification) => {
                    if (notification.isNotDisplayed || notification.isSkippedMoment) {
                      console.error('[GoogleSignIn] GoogleOneTap not available:', notification);
                      onError?.('Google Sign-In לא זמין. בדוק שה-origin מוגדר ב-Google Cloud Console.');
                    }
                  });
                });
              }
            }

            throw renderErr;
          }
        } catch (renderErr) {
          console.error(
            '[GoogleSignIn] Button rendering error:',
            renderErr instanceof Error ? renderErr.message : renderErr
          );
        }
      }
    } catch (err) {
      console.error('[GoogleSignIn] Google Sign-In button error:', err instanceof Error ? err.message : err);
      const currentOrigin = window.location.origin;
      onError?.(
        `שגיאה ביצירת כפתור Google Sign-In. Origin: ${currentOrigin}. בדוק שה-origin מוגדר ב-Google Cloud Console.`
      );
    }
  }, [scriptLoaded, initialized, disabled, onError]);

  return {
    buttonRef,
    scriptLoaded,
    loading,
    disabled,
  };
}
