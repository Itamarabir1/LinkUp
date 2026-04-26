import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import PageLoading from '../../../components/PageLoading';

/**
 */
export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user, isLoading } = useAuth();

  if (isLoading) return <PageLoading />;
  if (!user) {
    const from = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?from=${from}`} replace />;
  }
  if (!user.is_admin) return <Navigate to="/" replace />;

  return <>{children}</>;
}
