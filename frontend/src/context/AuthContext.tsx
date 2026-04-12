import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import {
  loginWithPassword,
  logoutSession,
  registerUser,
  signInWithGoogleToken,
} from '../api/auth';
import { clearTokens, setTokens } from '../api/client';
import { STORAGE_KEYS } from '../config/constants';
import { fetchCurrentUser, patchFcmToken } from '../api/users';
import { cleanupFCM, initFCM } from '../services/fcm';
import type { User } from '../types/api';

type AuthState = {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
};

export interface RegisterData {
  full_name: string;
  email: string;
  phone_number: string;
  password: string;
  confirm_password: string;
}

type AuthContextValue = AuthState & {
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  signInWithGoogle: (idToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    if (!token) {
      setState((s) => ({
        ...s,
        user: null,
        isAuthenticated: false,
        isLoading: false,
      }));
      return;
    }
    try {
      const { data } = await fetchCurrentUser();
      setState((s) => ({
        ...s,
        user: data,
        isAuthenticated: true,
        isLoading: false,
      }));
    } catch {
      clearTokens();
      setState((s) => ({
        ...s,
        user: null,
        isAuthenticated: false,
        isLoading: false,
      }));
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    if (!token || !mounted) {
      if (mounted) queueMicrotask(() => setState((s) => ({ ...s, isLoading: false })));
      return;
    }
    fetchCurrentUser()
      .then(({ data }) => {
        if (mounted) {
          setState({ user: data, isAuthenticated: true, isLoading: false });
          if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
            void initFCM();
          }
        }
      })
      .catch(() => {
        clearTokens();
        if (mounted) setState({ user: null, isAuthenticated: false, isLoading: false });
      });
    return () => {
      mounted = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await loginWithPassword(email, password);
    setTokens(data.access_token, data.refresh_token);
    setState({ user: data.user, isAuthenticated: true, isLoading: false });
    if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      void initFCM();
    }
  }, []);

  const register = useCallback(async (payload: RegisterData) => {
    await registerUser(payload);
  }, []);

  const signInWithGoogle = useCallback(async (idToken: string) => {
    const { data } = await signInWithGoogleToken(idToken);
    setTokens(data.access_token, data.refresh_token);
    setState({ user: data.user, isAuthenticated: true, isLoading: false });
    if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      void initFCM();
    }
  }, []);

  const logout = useCallback(async () => {
    // 1. Clear FCM token on server while JWT is still valid
    try {
      await patchFcmToken(null);
    } catch {
      // ignore
    }
    cleanupFCM();
    // 2. Invalidate server session
    try {
      await logoutSession();
    } catch {
      // ignore
    }
    // 3. Clear local tokens
    clearTokens();
    setState({ user: null, isAuthenticated: false, isLoading: false });
  }, []);

  const value: AuthContextValue = {
    ...state,
    login,
    register,
    signInWithGoogle,
    logout,
    refreshUser,
  };

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
