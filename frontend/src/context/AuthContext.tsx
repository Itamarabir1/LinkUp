import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { api, clearTokens, setTokens } from '../api/client';
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
    const token = localStorage.getItem('linkup_access_token');
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
      const { data } = await api.get<User>('/users/me');
      setState((s) => ({
        ...s,
        user: data,
        isAuthenticated: true,
        isLoading: false,
      }));
    } catch {
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
    const token = localStorage.getItem('linkup_access_token');
    if (!token || !mounted) {
      if (mounted) queueMicrotask(() => setState((s) => ({ ...s, isLoading: false })));
      return;
    }
    api
      .get<User>('/users/me')
      .then(({ data }) => {
        if (mounted)
          setState({ user: data, isAuthenticated: true, isLoading: false });
      })
      .catch(async () => {
        await clearTokens();
        if (mounted)
          setState({ user: null, isAuthenticated: false, isLoading: false });
      });
    return () => {
      mounted = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<{
      access_token: string;
      refresh_token: string;
      user: User;
    }>('/auth/login', { email, password });
    setTokens(data.access_token, data.refresh_token);
    setState({ user: data.user, isAuthenticated: true, isLoading: false });
  }, []);

  const register = useCallback(async (payload: RegisterData) => {
    await api.post('/auth/register', payload);
    // אחרי הרשמה עוברים למסך אימות אימייל – בלי התחברות אוטומטית
  }, []);

  const signInWithGoogle = useCallback(async (idToken: string) => {
    // הגדלת timeout ל-60 שניות עבור Google Sign-In (יכול לקחת זמן בגלל אימות עם Google)
    const { data } = await api.post<{
      access_token: string;
      refresh_token: string;
      user: User;
    }>('/auth/google-signin', { id_token: idToken }, { timeout: 60000 });
    setTokens(data.access_token, data.refresh_token);
    setState({ user: data.user, isAuthenticated: true, isLoading: false });
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // ignore
    }
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
