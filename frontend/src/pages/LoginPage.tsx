import { FormEvent, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { login } from '../api/auth';
import { setToken } from '../api/config';
import { useAuth } from '../contexts/AuthContext';
import { useI18n } from '../i18n';

export function LoginPage() {
  const [loginValue, setLoginValue] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { refresh } = useAuth();
  const { t } = useI18n();

  const next = params.get('next');
  const safeNext = next && next.startsWith('/') && !next.startsWith('//') ? next : '/';

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await login(loginValue.trim(), password);
      setToken(response.token);
      await refresh();
      navigate(safeNext, { replace: true });
    } catch (err) {
      setError((err as Error).message || t('login.invalid'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="card login-card">
        <img src="/favicon.svg" width={48} height={48} alt="" style={{ display: 'block', margin: '0 auto 12px' }} />
        <h1 className="login-card__title">Ibis</h1>
        <p className="login-card__subtitle">{t('login.subtitle')}</p>
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label className="form-label" htmlFor="login">
              {t('login.login')}
            </label>
            <input
              id="login"
              className="form-input"
              value={loginValue}
              onChange={(e) => setLoginValue(e.target.value)}
              autoComplete="username"
              autoCapitalize="none"
              autoCorrect="off"
              required
            />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="password">
              {t('login.password')}
            </label>
            <input
              id="password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          {error && <p className="form-error" style={{ marginBottom: 12 }}>{error}</p>}
          <button type="submit" className="button button--primary button--large button--block" disabled={loading}>
            {loading ? t('login.signingIn') : t('login.signIn')}
          </button>
        </form>
      </div>
    </div>
  );
}
