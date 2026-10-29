import { FormEvent, useCallback, useEffect, useState } from 'react';
import { createMember, listMembers, resetMemberPassword, updateMember } from '../../api/households';
import type { Member, Role } from '../../api/types';
import { useAuth } from '../../contexts/AuthContext';
import { useMessage } from '../../contexts/MessageContext';
import { ROLE_LABELS } from '../../utils/format';
import { EditMemberModal } from './EditMemberModal';

const ROLES: Role[] = ['manager', 'resident', 'guest', 'viewer'];

export function MembersSection({ householdId }: { householdId: string }) {
  const [members, setMembers] = useState<Member[] | null>(null);
  const [editing, setEditing] = useState<Member | null>(null);
  const showMessage = useMessage();
  const { me } = useAuth();

  const load = useCallback(() => {
    listMembers(householdId)
      .then(setMembers)
      .catch((e: Error) => showMessage('error', e.message));
  }, [householdId, showMessage]);

  useEffect(load, [load]);

  const change = async (member: Member, data: { role?: Role; is_active?: boolean }) => {
    try {
      await updateMember(householdId, member.id, data);
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  const resetPassword = async (member: Member) => {
    const password = window.prompt(`New password for ${member.display_name} (min. 4 characters)`);
    if (!password) return;
    try {
      await resetMemberPassword(householdId, member.id, password);
      showMessage('success', `Password changed for ${member.display_name}`);
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  return (
    <>
      <section className="card">
        <h2 className="card__title" style={{ marginBottom: 6 }}>
          Members
        </h2>
        <p className="muted small" style={{ marginBottom: 8 }}>
          Managers manage everything. Residents add costs. Guests take part in costs. Viewers only look. Disabled people can't sign
          in but stay in the history.
        </p>
        {!members && <p className="muted">Loading...</p>}
        <div className="list">
          {members?.map((m) => (
            <div key={m.id} className={`list-item ${m.is_active ? '' : 'list-item--disabled'}`}>
              <div className="list-item__main">
                <div className="list-item__title">
                  {m.display_name} {!m.is_active && <span className="pill">Disabled</span>}
                </div>
                <div className="list-item__sub">
                  @{m.login_name}
                  {m.bank_info ? ` · ${m.bank_info_type === 'pix' ? 'PIX' : 'Bank'}: ${m.bank_info}` : ' · no bank info'}
                </div>
              </div>
              <select
                className="form-select"
                style={{ width: 'auto' }}
                value={m.role}
                onChange={(e) => change(m, { role: e.target.value as Role })}
                aria-label={`Role of ${m.display_name}`}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABELS[r]}
                  </option>
                ))}
              </select>
              <button className="button button--secondary button--small" onClick={() => setEditing(m)}>
                Edit
              </button>
              <button className="button button--secondary button--small" onClick={() => change(m, { is_active: !m.is_active })}>
                {m.is_active ? 'Disable' : 'Enable'}
              </button>
              <button className="button button--ghost button--small" onClick={() => resetPassword(m)}>
                Reset password
              </button>
            </div>
          ))}
        </div>
      </section>
      <AddMemberForm householdId={householdId} isAdmin={!!me?.is_admin} onAdded={load} />
      {editing && <EditMemberModal householdId={householdId} member={editing} onSaved={load} onClose={() => setEditing(null)} />}
    </>
  );
}

function AddMemberForm({ householdId, isAdmin, onAdded }: { householdId: string; isAdmin: boolean; onAdded: () => void }) {
  const empty = { login_name: '', display_name: '', password: '', role: 'resident' as Role, email: '', whatsapp: '' };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const showMessage = useMessage();
  const set = (key: keyof typeof empty) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await createMember(householdId, {
        login_name: form.login_name.trim(),
        display_name: form.display_name.trim() || undefined,
        password: form.password || undefined,
        role: form.role,
        email: form.email.trim() || undefined,
        whatsapp: form.whatsapp.trim() || undefined,
      });
      showMessage('success', `${form.display_name || form.login_name} added`);
      setForm(empty);
      onAdded();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="card" onSubmit={submit}>
      <h2 className="card__title" style={{ marginBottom: 6 }}>
        Add a person
      </h2>
      <p className="muted small" style={{ marginBottom: 14 }}>
        Creates their account. Share the login and password with them.
        {isAdmin && ' As admin, you can also type an existing login to add that person here (no password needed).'}
      </p>
      <div className="form-grid form-grid--2">
        <div className="form-field">
          <label className="form-label" htmlFor="m-login">
            Login
          </label>
          <input id="m-login" className="form-input" value={form.login_name} onChange={set('login_name')} autoCapitalize="none" required />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="m-name">
            Name
          </label>
          <input id="m-name" className="form-input" value={form.display_name} onChange={set('display_name')} />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="m-pass">
            Password
          </label>
          <input id="m-pass" className="form-input" value={form.password} onChange={set('password')} autoComplete="new-password" />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="m-role">
            Role
          </label>
          <select id="m-role" className="form-select" value={form.role} onChange={set('role')}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="m-email">
            Email (optional)
          </label>
          <input id="m-email" type="email" className="form-input" value={form.email} onChange={set('email')} />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="m-wa">
            WhatsApp (optional)
          </label>
          <input id="m-wa" type="tel" className="form-input" value={form.whatsapp} onChange={set('whatsapp')} />
        </div>
      </div>
      {error && <p className="form-error" style={{ marginBottom: 12 }}>{error}</p>}
      <button className="button button--primary" disabled={saving}>
        {saving ? 'Adding...' : 'Add person'}
      </button>
    </form>
  );
}
