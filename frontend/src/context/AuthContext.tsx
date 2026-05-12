import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import * as Sentry from '@sentry/react';
import {
  loginWithPassword,
  logoutSession,
  registerUser,
  signInWithGoogleToken,
} from '../api/auth';
import { clearTokens, setTokens } from '../api/client';
import { STORAGE_KEYS } from '../config/constants';
import { qk } from '../api/queryKeys';
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
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const tearDownSession = useCallback(
    async (opts: { reason: 'user-action' | 'session-expired' | 'bootstrap-failed' }) => {
      if (opts.reason === 'user-action') {
        try {
          await patchFcmToken(null);
        } catch {
          /* ignore */
        }
        try {
          await logoutSession();
        } catch {
          /* ignore */
        }
      }
      cleanupFCM();
      queryClient.clear();
      if (import.meta.env.PROD) {
        Sentry.setUser(null);
      }
      clearTokens();
      setState({ user: null, isAuthenticated: false, isLoading: false });
    },
    [queryClient]
  );

  const refreshUser = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: qk.auth.me() });
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
      queryClient.setQueryData(qk.auth.me(), data);
      setState((s) => ({
        ...s,
        user: data,
        isAuthenticated: true,
        isLoading: false,
      }));
    } catch {
      await tearDownSession({ reason: 'bootstrap-failed' });
    }
  }, [queryClient, tearDownSession]);

  useEffect(() => {
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    if (!token) {
      queueMicrotask(() => setState((s) => ({ ...s, isLoading: false })));
      return;
    }
    const controller = new AbortController();
    fetchCurrentUser({ signal: controller.signal })
      .then(({ data }) => {
        if (controller.signal.aborted) return;
        queryClient.setQueryData(qk.auth.me(), data);
        setState({ user: data, isAuthenticated: true, isLoading: false });
        if (import.meta.env.PROD) {
          Sentry.setUser({ id: data.user_id });
        }
        void initFCM();
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        void tearDownSession({ reason: 'bootstrap-failed' });
      });
    return () => controller.abort();
  }, [queryClient, tearDownSession]);

  useEffect(() => {
    const handler = () => {
      void tearDownSession({ reason: 'session-expired' });
    };
    window.addEventListener('auth:session-expired', handler);
    return () => window.removeEventListener('auth:session-expired', handler);
  }, [tearDownSession]);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await loginWithPassword(email, password);
    setTokens(data.access_token);
    queryClient.setQueryData(qk.auth.me(), data.user);
    setState({ user: data.user, isAuthenticated: true, isLoading: false });
    if (import.meta.env.PROD) {
      Sentry.setUser({ id: data.user.user_id });
    }
    void initFCM();
  }, [queryClient]);

  const register = useCallback(async (payload: RegisterData) => {
    await registerUser(payload);
  }, []);

  const signInWithGoogle = useCallback(async (idToken: string) => {
    const { data } = await signInWithGoogleToken(idToken);
    setTokens(data.access_token);
    queryClient.setQueryData(qk.auth.me(), data.user);
    setState({ user: data.user, isAuthenticated: true, isLoading: false });
    if (import.meta.env.PROD) {
      Sentry.setUser({ id: data.user.user_id });
    }
    void initFCM();
  }, [queryClient]);

  const logout = useCallback(async () => {
    await tearDownSession({ reason: 'user-action' });
  }, [tearDownSession]);

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

export function useCurrentUser() {
  return useQuery({
    queryKey: qk.auth.me(),
    queryFn: async ({ signal }) => {
      const { data } = await fetchCurrentUser({ signal });
      return data;
    },
    enabled: !!localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN),
    staleTime: 5 * 60_000,
  });
}
