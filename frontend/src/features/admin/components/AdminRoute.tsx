import { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import PageLoading from '../../../components/PageLoading';

/**
 * אדמין דורש משתמש מחובר + is_admin.
 * אחרי login/google המשתמש ב-context לפעמים מגיע בלי is_admin (LoginUserInfo) —
 * אז מרעננים פרופיל מ־GET /users/me (UserRead כולל is_admin).
 */
export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user, isLoading, refreshUser } = useAuth();
  const [profileReady, setProfileReady] = useState(false);
  const isAdminDefined = user?.is_admin !== undefined;

  useEffect(() => {
    let cancelled = false;
    if (isLoading) return;
    if (!user) {
      setProfileReady(true);
      return;
    }
    if (user.is_admin !== undefined) {
      setProfileReady(true);
      return;
    }
    refreshUser()
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setProfileReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [isLoading, !!user, isAdminDefined, refreshUser]);

  if (isLoading || !profileReady) return <PageLoading />;
  if (!user) {
    const from = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?from=${from}`} replace />;
  }
  if (!user.is_admin) return <Navigate to="/" replace />;

  return <>{children}</>;
}
