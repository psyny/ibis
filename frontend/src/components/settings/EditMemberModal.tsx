import { FormEvent, useState } from 'react';
import { updateMember } from '../../api/households';
import type { BankInfoType, Member, Role } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
import { MessageKey, useI18n } from '../../i18n';
import { BankInfoFields, bankInfoError, normalizeBankInfo } from '../BankInfoFields';
import { Modal } from '../Modal';

const ROLES: Role[] = ['manager', 'resident', 'guest', 'viewer'];

interface Props {
  householdId: string;
  member: Member;
  onSaved: () => void;
  onClose: () => void;
}

/** Managers/admins edit a person: name, role, contact and bank info. */
export function EditMemberModal({ householdId, member, onSaved, onClose }: Props) {
  const [form, setForm] = useState({
    display_name: member.display_name,
    email: member.email || '',
    whatsapp: member.whatsapp || '',
    bank_info: member.bank_info || '',
  });
  const [bankType, setBankType] = useState<BankInfoType>(member.bank_info_type || 'pix');
  const [role, setRole] = useState<Role>(member.role);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const showMessage = useMessage();
  const { t } = useI18n();
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.display_name.trim()) return setError(t('validation.name'));
    const bankProblem = bankInfoError(t, bankType, form.bank_info);
    if (bankProblem) return setError(bankProblem);
    setError('');
    setSaving(true);
    try {
      await updateMember(householdId, member.id, {
        ...form,
        display_name: form.display_name.trim(),
        bank_info: normalizeBankInfo(bankType, form.bank_info),
        bank_info_type: bankType,
        ...(role !== member.role ? { role } : {}),
      });
      showMessage('success', t('members.saved', { name: form.display_name.trim() }));
      onSaved();
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={t('members.editTitle', { name: member.display_name })} onClose={onClose}>
      <form onSubmit={submit}>
        <p className="muted small" style={{ marginBottom: 12 }}>
          {t('members.loginLabel', { login: member.login_name })}
        </p>
        <div className="form-field">
          <label className="form-label" htmlFor="e-name">
            {t('common.name')}
          </label>
          <input id="e-name" className="form-input" value={form.display_name} onChange={set('display_name')} required />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="e-role">
            {t('common.role')}
          </label>
          <select id="e-role" className="form-select" value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {t(`role.${r}` as MessageKey)}
              </option>
            ))}
          </select>
        </div>
        <BankInfoFields
          idPrefix="e"
          type={bankType}
          value={form.bank_info}
          onTypeChange={setBankType}
          onValueChange={(bank_info) => setForm({ ...form, bank_info })}
        />
        <div className="form-field">
          <label className="form-label" htmlFor="e-wa">
            {t('common.whatsapp')}
          </label>
          <input id="e-wa" type="tel" className="form-input" value={form.whatsapp} onChange={set('whatsapp')} />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="e-email">
            {t('common.email')}
          </label>
          <input id="e-email" type="email" className="form-input" value={form.email} onChange={set('email')} />
        </div>
        {error && <p className="form-error">{error}</p>}
        <div className="modal__actions">
          <button type="button" className="button button--ghost" onClick={onClose}>
            {t('common.cancel')}
          </button>
          <button className="button button--primary" disabled={saving}>
            {saving ? t('common.saving') : t('common.save')}
          </button>
        </div>
      </form>
    </Modal>
  );
}
