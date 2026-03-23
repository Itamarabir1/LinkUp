import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { ERROR_MESSAGES } from '../config/constants';

interface GoogleSignInProps {
  onError?: (error: string) => void;
  disabled?: boolean;
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { 
            client_id: string; 
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
            itp_support?: boolean;
          }) => void;
          renderButton: (element: HTMLElement, config: { theme?: string; size?: string; text?: string; width?: number }) => void;
          prompt: (callback?: (notification: { isNotDisplayed: boolean; isSkippedMoment: boolean; dismissedMoment?: number; skippedMoment?: number }) => void) => void;
          disableAutoSelect: () => void;
        };
      };
    };
  }
}

export default function GoogleSignIn({ onError, disabled }: GoogleSignInProps) {
  const [loading, setLoading] = useState(false);
  const [scriptLoaded, setScriptLoaded] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const { signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const buttonRef = useRef<HTMLDivElement>(null);
  const callbackRef = useRef<((response: { credential: string }) => Promise<void>) | null>(null);
  const initializedRef = useRef(false); // מונע קריאות כפולות

  // טעינת Google Identity Services script רק כשה-component נטען
  useEffect(() => {
    const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!googleClientId) {
      console.error('VITE_GOOGLE_CLIENT_ID not set in environment variables');
      if (onError) {
        onError('Google Client ID לא מוגדר. אנא הגדר VITE_GOOGLE_CLIENT_ID ב-.env');
      }
      return;
    }

    // בדיקה אם כבר אתחלנו - מונע קריאות כפולות
    if (initialized || scriptLoaded) {
      return;
    }

    // פונקציה לאתחול Google Identity Services (מונעת קריאות כפולות)
    const initializeGoogleSignIn = () => {
      if (!window.google?.accounts?.id) {
        console.error('[GoogleSignIn] Google Identity Services API not available');
        return false;
      }
      
      // בדיקה אם כבר אתחלנו (מונע קריאות כפולות באותו mount)
      if (initializedRef.current) {
        return true;
      }

      const currentOrigin = window.location.origin;

      try {
        // אתחול עם הגדרות נוספות שיכולות לעזור
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: async (response: { credential: string }) => {
            if (callbackRef.current) {
              await callbackRef.current(response);
            }
          },
          auto_select: false,
          cancel_on_tap_outside: true,
          itp_support: true, // תמיכה ב-Intelligent Tracking Prevention
        });
        initializedRef.current = true;
        setInitialized(true);
        return true;
      } catch (err) {
        console.error('[GoogleSignIn] ❌ Failed to initialize Google Identity Services:', err);
        const msg = err instanceof Error ? err.message : String(err);
        const isOriginError = /origin|not allowed|403|client id/i.test(msg);
        if (isOriginError && onError) {
          const originMsg = `ה-origin לא מורשה ב-Google. Origin: ${currentOrigin}. Client ID: ${googleClientId}. הוסף בדיוק את ה-origin הזה ב-Google Cloud Console → Credentials → ה-Client ID → Authorized JavaScript origins.`;
          onError(originMsg);
        }
        if (err instanceof Error) {
          console.error('[GoogleSignIn] Error message:', err.message);
          console.error('[GoogleSignIn] Error stack:', err.stack);
        }
        return false;
      }
    };

    // בדיקה אם ה-script כבר נטען
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
      // מחכים שה-script יסיים לטעון ואז מאתחלים מיד
      let checkCount = 0;
      const maxChecks = 50; // 5 שניות
      const checkInterval = setInterval(() => {
        checkCount++;
        if (window.google?.accounts?.id) {
          clearInterval(checkInterval);
          initializeGoogleSignIn();
          setScriptLoaded(true);
        } else if (checkCount >= maxChecks) {
          clearInterval(checkInterval);
          console.error('Google Identity Services failed to load after timeout');
          if (onError) {
            onError('Google Sign-In לא נטען. אנא רענן את הדף.');
          }
        }
      }, 100);
      return () => {
        clearInterval(checkInterval);
        setInitialized(false);
        setScriptLoaded(false);
        initializedRef.current = false;
      };
    }

    // טעינת ה-script
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      // מחכים קצת כדי לוודא שה-API זמין ואז מאתחלים מיד
      setTimeout(() => {
        if (window.google?.accounts?.id) {
          initializeGoogleSignIn();
          setScriptLoaded(true);
        } else {
          console.error('Google Identity Services API not available after script load');
          if (onError) {
            onError('Google Sign-In לא זמין. אנא רענן את הדף.');
          }
        }
      }, 100);
    };
    script.onerror = () => {
      console.error('Failed to load Google Identity Services script (may be 403 - origin not allowed)');
      if (onError) {
        const origin = window.location.origin;
        onError(`טעינת Google Sign-In נכשלה. Origin: ${origin}. Client ID: ${googleClientId}. בדוק שה-origin מורשה עבור ה-Client ID הזה ב-Google Cloud Console → Credentials → Authorized JavaScript origins.`);
      }
    };
    document.head.appendChild(script);

    return () => {
      // לא מוחקים את ה-script כי הוא יכול להיות בשימוש במקומות אחרים
      setInitialized(false);
      setScriptLoaded(false);
      initializedRef.current = false;
    };
  }, [onError]); // eslint-disable-line react-hooks/exhaustive-deps -- intentional: effect runs once on mount, initialized/scriptLoaded are managed internally

  // הגדרת ה-callback
  useEffect(() => {
    callbackRef.current = async (response: { credential: string }) => {
      setLoading(true);
      try {
        await signInWithGoogle(response.credential);
        navigate('/', { replace: true });
      } catch (err: unknown) {
        const error = err as { code?: string; message?: string; response?: { data?: { detail?: string } } };
        if ((error.code === 'ECONNABORTED' || (error.message && error.message.includes('timeout'))) && onError) {
          onError(ERROR_MESSAGES.BACKEND_TIMEOUT);
          return;
        }
        const errorMessage = error.response?.data?.detail || error.message || 'התחברות נכשלה';
        if (onError) {
          onError(errorMessage);
        }
      } finally {
        setLoading(false);
      }
    };
  }, [signInWithGoogle, navigate, onError]);

  // רינדור הכפתור כשה-script נטען ואתחלנו
  useEffect(() => {
    if (!scriptLoaded || !initialized || !buttonRef.current || disabled) return;

    const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!googleClientId) return;

    try {
      if (buttonRef.current) {
        const currentOrigin = window.location.origin;
        
        // ניקוי הכפתור הקודם אם יש
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
            console.error('[GoogleSignIn] renderButton failed, using fallback:', renderErr instanceof Error ? renderErr.message : renderErr);
            const renderMsg = renderErr instanceof Error ? renderErr.message : String(renderErr);
            const isOriginError = /origin|not allowed|403|client id/i.test(renderMsg);
            if (isOriginError && onError) {
              const originMsg = `ה-origin לא מורשה ב-Google. הוסף בדיוק את הכתובת הזו ב-Google Cloud Console → Credentials → ה-Client ID → Authorized JavaScript origins: ${currentOrigin}`;
              onError(originMsg);
            }
            // אם renderButton נכשל, ננסה ליצור כפתור ידני עם GoogleOneTap
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
                      if (onError) {
                        onError('Google Sign-In לא זמין. בדוק שה-origin מוגדר ב-Google Cloud Console.');
                      }
                    }
                  });
                });
              }
            }
            
            throw renderErr;
          }
        } catch (renderErr) {
          console.error('[GoogleSignIn] Button rendering error:', renderErr instanceof Error ? renderErr.message : renderErr);
          // לא זורקים שגיאה כאן כדי שהכפתור הידני יוכל לעבוד
        }
      }
    } catch (err) {
      console.error('[GoogleSignIn] Google Sign-In button error:', err instanceof Error ? err.message : err);
      const currentOrigin = window.location.origin;
      if (onError) {
        onError(`שגיאה ביצירת כפתור Google Sign-In. Origin: ${currentOrigin}. בדוק שה-origin מוגדר ב-Google Cloud Console.`);
      }
    }
  }, [scriptLoaded, initialized, disabled, onError]);

  if (!scriptLoaded) {
    return (
      <div
        ref={buttonRef}
        style={{
          width: '100%',
          minHeight: '40px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {loading ? 'מתחבר...' : 'טוען Google Sign-In...'}
      </div>
    );
  }

  return (
    <div
      ref={buttonRef}
      style={{
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
        opacity: disabled ? 0.6 : 1,
        pointerEvents: disabled ? 'none' : 'auto',
      }}
    />
  );
}
