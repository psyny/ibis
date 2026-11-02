import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { createHousehold, createUser, deleteHousehold, listAllHouseholds, listUsers, updateUser } from '../api/admin';
import type { AdminHousehold, UserInfo } from '../api/types';
import { TopBar } from '../components/TopBar';
import { useAuth } from '../contexts/AuthContext';
import { useMessage } from '../contexts/MessageContext';
import { LanguageCode, LANGUAGES, useI18n } from '../i18n';

/** App admin: create households and manage accounts. */
export function AdminPage() {
  const { me, refresh } = useAuth();
  const showMessage = useMessage();
  const { t, tn } = useI18n();
  const [households, setHouseholds] = useState<AdminHousehold[] | null>(null);
  const [users, setUsers] = useState<UserInfo[] | null>(null);
  const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  const [hForm, setHForm] = useState({ name: '', currency: 'BRL', timezone: browserTz, auto_close_days: '', language: 'en' as LanguageCode });
  const [uForm, setUForm] = useState({ login_name: '', display_name: '', password: '', is_admin: false });

  const load = useCallback(() => {
    Promise.all([listAllHouseholds(), listUsers()])
      .then(([h, u]) => {
        setHouseholds(h);
        setUsers(u);
      })
      .catch((e: Error) => showMessage('error', e.message));
  }, [showMessage]);
  useEffect(load, [load]);

  if (me && !me.is_admin) return <Navigate to="/" replace />;

  const run = async (action: () => Promise<unknown>, success: string) => {
    try {
      await action();
      showMessage('success', success);
      load();
      refresh();
      return true;
    } catch (e) {
      showMessage('error', (e as Error).message);
      return false;
    }
  };

  const addHousehold = async (e: FormEvent) => {
    e.preventDefault();
    const days = hForm.auto_close_days.trim();
    const ok = await run(
      () =>
        createHousehold({
          name: hForm.name.trim(),
          currency: hForm.currency.trim().toUpperCase(),
          timezone: hForm.timezone.trim(),
          auto_close_days: days === '' ? null : Number(days),
          language: hForm.language,
        }),
      t('admin.householdCreated', { name: hForm.name }),
    );
    if (ok) setHForm({ ...hForm, name: '' });
  };

  const addUser = async (e: FormEvent) => {
    e.preventDefault();
    const ok = await run(() => createUser(uForm), t('admin.userCreated', { login: uForm.login_name }));
    if (ok) setUForm({ login_name: '', display_name: '', password: '', is_admin: false });
  };

  return (
    <>
      <TopBar />
      <main className="page">
        <div className="page__inner">
          <div>
            <h1 className="page-title">{t('menu.admin')}</h1>
            <p className="page-description">{t('admin.description')}</p>
          </div>

          <section className="card">
            <h2 className="card__title" style={{ marginBottom: 8 }}>
              {t('admin.households')}
            </h2>
            {!households && <p className="muted">{t('common.loading')}</p>}
            {households?.length === 0 && <p className="muted">{t('admin.noHouseholds')}</p>}
            <div className="list">
              {households?.map((h) => (
                <div key={h.id} className="list-item">
                  <div className="list-item__main">
                    <div className="list-item__title">
                      <Link to={`/h/${h.id}`}>{h.name}</Link>
                    </div>
                    <div className="list-item__sub">
                      {tn('admin.people', h.member_count)} · {h.currency} · {h.timezone} · {LANGUAGES.find((l) => l.code === h.language)?.label || h.language}
                      {h.auto_close_days !== null && ` · ${tn('admin.autoCloseAfter', h.auto_close_days)}`}
                    </div>
                  </div>
                  <Link to={`/h/${h.id}/settings`} className="button button--secondary button--small">
                    {t('settings.title')}
                  </Link>
                  <button
                    className="button button--danger button--small"
                    onClick={() =>
                      window.prompt(t('admin.deletePrompt', { name: h.name })) === h.name &&
                      run(() => deleteHousehold(h.id), t('admin.deleted', { name: h.name }))
                    }
                  >
                    {t('common.delete')}
                  </button>
                </div>
              ))}
            </div>
            <form onSubmit={addHousehold} style={{ marginTop: 16 }}>
              <div className="form-grid form-grid--2">
                <div className="form-field">
                  <label className="form-label" htmlFor="h-name">
                    {t('common.name')}
                  </label>
                  <input id="h-name" className="form-input" value={hForm.name} onChange={(e) => setHForm({ ...hForm, name: e.target.value })} required />
                </div>
                <div className="form-field">
                  <label className="form-label" htmlFor="h-cur">
                    {t('general.currency')}
                  </label>
                  <input
                    id="h-cur"
                    className="form-input"
                    maxLength={3}
                    value={hForm.currency}
                    onChange={(e) => setHForm({ ...hForm, currency: e.target.value.toUpperCase() })}
                    required
                  />
                </div>
                <div className="form-field">
                  <label className="form-label" htmlFor="h-tz">
                    {t('general.timezone')}
                  </label>
                  <input id="h-tz" className="form-input" value={hForm.timezone} onChange={(e) => setHForm({ ...hForm, timezone: e.target.value })} required />
                </div>
                <div className="form-field">
                  <label className="form-label" htmlFor="h-close">
                    {t('admin.autoCloseDays')}
                  </label>
                  <input
                    id="h-close"
                    className="form-input"
                    type="number"
                    min={0}
                    placeholder={t('admin.emptyNever')}
                    value={hForm.auto_close_days}
                    onChange={(e) => setHForm({ ...hForm, auto_close_days: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label className="form-label" htmlFor="h-lang">
                    {t('general.language')}
                  </label>
                  <select id="h-lang" className="form-select" value={hForm.language} onChange={(e) => setHForm({ ...hForm, language: e.target.value as LanguageCode })}>
                    {LANGUAGES.map((l) => (
                      <option key={l.code} value={l.code}>
                        {l.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <button className="button button--primary">{t('admin.createHousehold')}</button>
            </form>
          </section>

          <section className="card">
            <h2 className="card__title" style={{ marginBottom: 8 }}>
              {t('admin.accounts')}
            </h2>
            {!users && <p className="muted">{t('common.loading')}</p>}
            <div className="list">
              {users?.map((u) => (
                <div key={u.id} className={`list-item ${u.is_active ? '' : 'list-item--disabled'}`}>
                  <div className="list-item__main">
                    <div className="list-item__title">
                      {u.display_name} {u.is_admin && <span className="pill">{t('menu.admin')}</span>}{' '}
                      {!u.is_active && <span className="pill">{t('common.disabled')}</span>}
                    </div>
                    <div className="list-item__sub">@{u.login_name}</div>
                  </div>
                  {u.id !== me?.id && (
                    <>
                      <button
                        className="button button--secondary button--small"
                        onClick={() => run(() => updateUser(u.id, { is_admin: !u.is_admin }), t('common.saved'))}
                      >
                        {u.is_admin ? t('admin.removeAdmin') : t('admin.makeAdmin')}
                      </button>
                      <button
                        className="button button--secondary button--small"
                        onClick={() => run(() => updateUser(u.id, { is_active: !u.is_active }), t('common.saved'))}
                      >
                        {u.is_active ? t('common.disable') : t('common.enable')}
                      </button>
                    </>
                  )}
                  <button
                    className="button button--ghost button--small"
                    onClick={() => {
                      const password = window.prompt(t('members.newPasswordPrompt', { name: u.display_name }));
                      if (password) run(() => updateUser(u.id, { new_password: password }), t('members.passwordChangedFor', { name: u.display_name }));
                    }}
                  >
                    {t('members.resetPassword')}
                  </button>
                </div>
              ))}
            </div>
            <form onSubmit={addUser} style={{ marginTop: 16 }}>
              <p className="muted small" style={{ marginBottom: 10 }}>
                {t('admin.accountsHint')}
              </p>
              <div className="form-grid form-grid--3">
                <input className="form-input" placeholder={t('login.login')} value={uForm.login_name} onChange={(e) => setUForm({ ...uForm, login_name: e.target.value })} required />
                <input className="form-input" placeholder={t('common.name')} value={uForm.display_name} onChange={(e) => setUForm({ ...uForm, display_name: e.target.value })} required />
                <input
                  className="form-input"
                  placeholder={t('login.password')}
                  value={uForm.password}
                  minLength={4}
                  onChange={(e) => setUForm({ ...uForm, password: e.target.value })}
                  required
                />
              </div>
              <div className="row" style={{ marginTop: 10 }}>
                <label className="checkbox">
                  <input type="checkbox" checked={uForm.is_admin} onChange={(e) => setUForm({ ...uForm, is_admin: e.target.checked })} />
                  {t('menu.admin')}
                </label>
                <button className="button button--primary">{t('admin.createAccount')}</button>
              </div>
            </form>
          </section>
        </div>
      </main>
    </>
  );
}
