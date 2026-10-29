import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { createHousehold, createUser, deleteHousehold, listAllHouseholds, listUsers, updateUser } from '../api/admin';
import type { AdminHousehold, UserInfo } from '../api/types';
import { TopBar } from '../components/TopBar';
import { useAuth } from '../contexts/AuthContext';
import { useMessage } from '../contexts/MessageContext';

/** App admin: create households and manage accounts. */
export function AdminPage() {
  const { me, refresh } = useAuth();
  const showMessage = useMessage();
  const [households, setHouseholds] = useState<AdminHousehold[] | null>(null);
  const [users, setUsers] = useState<UserInfo[] | null>(null);
  const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  const [hForm, setHForm] = useState({ name: '', currency: 'BRL', timezone: browserTz, auto_close_days: '' });
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
        }),
      `Household ${hForm.name} created`,
    );
    if (ok) setHForm({ ...hForm, name: '' });
  };

  const addUser = async (e: FormEvent) => {
    e.preventDefault();
    const ok = await run(() => createUser(uForm), `User ${uForm.login_name} created`);
    if (ok) setUForm({ login_name: '', display_name: '', password: '', is_admin: false });
  };

  return (
    <>
      <TopBar />
      <main className="page">
        <div className="page__inner">
          <div>
            <h1 className="page-title">Admin</h1>
            <p className="page-description">Create households, then open their settings to add people.</p>
          </div>

          <section className="card">
            <h2 className="card__title" style={{ marginBottom: 8 }}>
              Households
            </h2>
            {!households && <p className="muted">Loading...</p>}
            {households?.length === 0 && <p className="muted">No households yet. Create the first one below.</p>}
            <div className="list">
              {households?.map((h) => (
                <div key={h.id} className="list-item">
                  <div className="list-item__main">
                    <div className="list-item__title">
                      <Link to={`/h/${h.id}`}>{h.name}</Link>
                    </div>
                    <div className="list-item__sub">
                      {h.member_count} people · {h.currency} · {h.timezone}
                      {h.auto_close_days !== null && ` · auto-close after ${h.auto_close_days} days`}
                    </div>
                  </div>
                  <Link to={`/h/${h.id}/settings`} className="button button--secondary button--small">
                    Settings
                  </Link>
                  <button
                    className="button button--danger button--small"
                    onClick={() =>
                      window.prompt(`This deletes ${h.name} and ALL its costs. Type the household name to confirm.`) === h.name &&
                      run(() => deleteHousehold(h.id), `${h.name} deleted`)
                    }
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
            <form onSubmit={addHousehold} style={{ marginTop: 16 }}>
              <div className="form-grid form-grid--2">
                <div className="form-field">
                  <label className="form-label" htmlFor="h-name">
                    Name
                  </label>
                  <input id="h-name" className="form-input" value={hForm.name} onChange={(e) => setHForm({ ...hForm, name: e.target.value })} required />
                </div>
                <div className="form-field">
                  <label className="form-label" htmlFor="h-cur">
                    Currency
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
                    Timezone
                  </label>
                  <input id="h-tz" className="form-input" value={hForm.timezone} onChange={(e) => setHForm({ ...hForm, timezone: e.target.value })} required />
                </div>
                <div className="form-field">
                  <label className="form-label" htmlFor="h-close">
                    Auto-close after (days)
                  </label>
                  <input
                    id="h-close"
                    className="form-input"
                    type="number"
                    min={0}
                    placeholder="Empty = never"
                    value={hForm.auto_close_days}
                    onChange={(e) => setHForm({ ...hForm, auto_close_days: e.target.value })}
                  />
                </div>
              </div>
              <button className="button button--primary">Create household</button>
            </form>
          </section>

          <section className="card">
            <h2 className="card__title" style={{ marginBottom: 8 }}>
              Accounts
            </h2>
            {!users && <p className="muted">Loading...</p>}
            <div className="list">
              {users?.map((u) => (
                <div key={u.id} className={`list-item ${u.is_active ? '' : 'list-item--disabled'}`}>
                  <div className="list-item__main">
                    <div className="list-item__title">
                      {u.display_name} {u.is_admin && <span className="pill">Admin</span>}{' '}
                      {!u.is_active && <span className="pill">Disabled</span>}
                    </div>
                    <div className="list-item__sub">@{u.login_name}</div>
                  </div>
                  {u.id !== me?.id && (
                    <>
                      <button
                        className="button button--secondary button--small"
                        onClick={() => run(() => updateUser(u.id, { is_admin: !u.is_admin }), 'Saved')}
                      >
                        {u.is_admin ? 'Remove admin' : 'Make admin'}
                      </button>
                      <button
                        className="button button--secondary button--small"
                        onClick={() => run(() => updateUser(u.id, { is_active: !u.is_active }), 'Saved')}
                      >
                        {u.is_active ? 'Disable' : 'Enable'}
                      </button>
                    </>
                  )}
                  <button
                    className="button button--ghost button--small"
                    onClick={() => {
                      const password = window.prompt(`New password for ${u.display_name} (min. 4 characters)`);
                      if (password) run(() => updateUser(u.id, { new_password: password }), 'Password changed');
                    }}
                  >
                    Reset password
                  </button>
                </div>
              ))}
            </div>
            <form onSubmit={addUser} style={{ marginTop: 16 }}>
              <p className="muted small" style={{ marginBottom: 10 }}>
                Usually people are added from a household's settings. Use this for other admins.
              </p>
              <div className="form-grid form-grid--3">
                <input className="form-input" placeholder="Login" value={uForm.login_name} onChange={(e) => setUForm({ ...uForm, login_name: e.target.value })} required />
                <input className="form-input" placeholder="Name" value={uForm.display_name} onChange={(e) => setUForm({ ...uForm, display_name: e.target.value })} required />
                <input
                  className="form-input"
                  placeholder="Password"
                  value={uForm.password}
                  minLength={4}
                  onChange={(e) => setUForm({ ...uForm, password: e.target.value })}
                  required
                />
              </div>
              <div className="row" style={{ marginTop: 10 }}>
                <label className="checkbox">
                  <input type="checkbox" checked={uForm.is_admin} onChange={(e) => setUForm({ ...uForm, is_admin: e.target.checked })} />
                  Admin
                </label>
                <button className="button button--primary">Create account</button>
              </div>
            </form>
          </section>
        </div>
      </main>
    </>
  );
}
