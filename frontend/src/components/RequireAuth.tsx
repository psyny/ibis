import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { getToken } from '../api/config';
import { useAuth } from '../contexts/AuthContext';
import { useI18n } from '../i18n';

/** Protects routes. Unauthenticated visitors go to /login and come back here afterwards. */
export function RequireAuth() {
  const { me, loading } = useAuth();
  const { t } = useI18n();
  const location = useLocation();
  const next = encodeURIComponent(location.pathname + location.search);

  if (!getToken()) return <Navigate to={`/login?next=${next}`} replace />;
  if (loading) return <div className="state-message">{t('common.loading')}</div>;
  if (!me) return <Navigate to={`/login?next=${next}`} replace />;
  return <Outlet />;
}
