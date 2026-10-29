import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { getToken } from '../api/config';
import { useAuth } from '../contexts/AuthContext';

/** Protects routes. Unauthenticated visitors go to /login and come back here afterwards. */
export function RequireAuth() {
  const { me, loading } = useAuth();
  const location = useLocation();
  const next = encodeURIComponent(location.pathname + location.search);

  if (!getToken()) return <Navigate to={`/login?next=${next}`} replace />;
  if (loading) return <div className="state-message">Loading...</div>;
  if (!me) return <Navigate to={`/login?next=${next}`} replace />;
  return <Outlet />;
}
