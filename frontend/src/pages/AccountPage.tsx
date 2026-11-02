import { ChangeEvent, FormEvent, useState } from 'react';
import { changePassword, signOutEverywhere, updateProfile } from '../api/auth';
import type { BankInfoType } from '../api/types';
import { BankInfoFields, bankInfoError, normalizeBankInfo } from '../components/BankInfoFields';
import { ConfirmModal } from '../components/ConfirmModal';
import { TopBar } from '../components/TopBar';
import { lastHousehold, useAuth } from '../contexts/AuthContext';
import { useMessage } from '../contexts/MessageContext';
import { useI18n } from '../i18n';
import { resizeImage } from '../utils/image';

/** The user's own account: contact and payment info shown to their household, and password. */
export function AccountPage() {
  const { me, refresh } = useAuth();
  const showMessage = useMessage();
  const { t } = useI18n();
  const [form, setForm] = useState({
    display_name: me?.display_name || '',
    email: me?.email || '',
    whatsapp: me?.whatsapp || '',
    bank_info: me?.bank_info || '',
  });
  const [bankType, setBankType] = useState<BankInfoType>(me?.bank_info_type || 'pix');
  const [qr, setQr] = useState<string | null>(me?.transfer_qr || null);
  const [saving, setSaving] = useState(false);
  const [passwords, setPasswords] = useState({ current: '', next: '' });

  const householdId = lastHousehold() || me?.households[0]?.id;
  const set = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value });

  const pickQr = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    try {
      setQr(await resizeImage(file, 600));
    } catch (err) {
      showMessage('error', (err as Error).message);
    }
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    const bankProblem = bankInfoError(t, bankType, form.bank_info);
    if (bankProblem) return showMessage('error', bankProblem);
    setSaving(true);
    const bank_info = normalizeBankInfo(bankType, form.bank_info);
    setForm((f) => ({ ...f, bank_info }));
    try {
      await updateProfile({
        ...form,
        bank_info,
        bank_info_type: bankType,
        transfer_qr: qr || '',
      });
      await refresh();
      showMessage('success', t('account.saved'));
    } catch (err) {
      showMessage('error', (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const savePassword = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await changePassword(passwords.current, passwords.next);
      setPasswords({ current: '', next: '' });
      showMessage('success', t('account.passwordChanged'));
    } catch (err) {
      showMessage('error', (err as Error).message);
    }
  };

  const [confirmSignOut, setConfirmSignOut] = useState(false);

  const current = me?.households.find((h) => h.id === householdId);

  return (
    <>
      <TopBar householdId={householdId} householdName={current?.name} canManage={current?.role === 'manager'} />
      <main className="page">
        <div className="page__inner page__inner--narrow">
          <div>
            <h1 className="page-title">{t('menu.myAccount')}</h1>
            <p className="page-description">{t('account.description', { login: me?.login_name || '' })}</p>
          </div>

          <form className="card" onSubmit={save}>
            <div className="form-field">
              <label className="form-label" htmlFor="a-name">
                {t('common.name')}
              </label>
              <input id="a-name" className="form-input" value={form.display_name} onChange={set('display_name')} required />
            </div>
            <BankInfoFields
              idPrefix="a"
              type={bankType}
              value={form.bank_info}
              onTypeChange={setBankType}
              onValueChange={(bank_info) => setForm({ ...form, bank_info })}
            />
            <div className="form-grid form-grid--2">
              <div className="form-field">
                <label className="form-label" htmlFor="a-wa">
                  {t('common.whatsapp')}
                </label>
                <input id="a-wa" type="tel" className="form-input" value={form.whatsapp} onChange={set('whatsapp')} placeholder="+55 11 99999-9999" />
              </div>
              <div className="form-field">
                <label className="form-label" htmlFor="a-email">
                  {t('common.email')}
                </label>
                <input id="a-email" type="email" className="form-input" value={form.email} onChange={set('email')} />
              </div>
            </div>
            <div className="form-field">
              <span className="form-label">{t('contact.qr')}</span>
              {qr ? (
                <img src={qr} alt={t('account.qrAlt')} className="qr-image" style={{ margin: '4px 0 8px', maxWidth: 200 }} />
              ) : (
                <span className="form-hint">{t('account.qrHint')}</span>
              )}
              <div className="row">
                <label className="button button--secondary button--small">
                  {qr ? t('account.replaceImage') : t('account.uploadImage')}
                  <input type="file" accept="image/*" onChange={pickQr} className="visually-hidden" />
                </label>
                {qr && (
                  <button type="button" className="button button--ghost button--small" onClick={() => setQr(null)}>
                    {t('common.remove')}
                  </button>
                )}
              </div>
            </div>
            <button className="button button--primary" disabled={saving}>
              {saving ? t('common.saving') : t('common.save')}
            </button>
          </form>

          <form className="card" onSubmit={savePassword}>
            <h2 className="card__title" style={{ marginBottom: 14 }}>
              {t('account.changePassword')}
            </h2>
            <div className="form-grid form-grid--2">
              <div className="form-field">
                <label className="form-label" htmlFor="p-current">
                  {t('account.currentPassword')}
                </label>
                <input
                  id="p-current"
                  type="password"
                  className="form-input"
                  autoComplete="current-password"
                  value={passwords.current}
                  onChange={(e) => setPasswords({ ...passwords, current: e.target.value })}
                  required
                />
              </div>
              <div className="form-field">
                <label className="form-label" htmlFor="p-next">
                  {t('account.newPassword')}
                </label>
                <input
                  id="p-next"
                  type="password"
                  className="form-input"
                  autoComplete="new-password"
                  minLength={4}
                  value={passwords.next}
                  onChange={(e) => setPasswords({ ...passwords, next: e.target.value })}
                  required
                />
              </div>
            </div>
            <p className="form-hint" style={{ marginBottom: 12 }}>
              {t('account.passwordHint')}
            </p>
            <button className="button button--secondary">{t('account.changePassword')}</button>
          </form>

          <section className="card">
            <h2 className="card__title" style={{ marginBottom: 6 }}>
              {t('account.devices')}
            </h2>
            <p className="muted small" style={{ marginBottom: 12 }}>
              {t('account.devicesHint')}
            </p>
            <button className="button button--danger" onClick={() => setConfirmSignOut(true)}>
              {t('account.signOutOthers')}
            </button>
          </section>
        </div>
      </main>
      {confirmSignOut && (
        <ConfirmModal
          title={t('account.signOutOthersConfirm')}
          confirmLabel={t('account.signThemOut')}
          danger
          onClose={() => setConfirmSignOut(false)}
          onConfirm={async () => {
            try {
              await signOutEverywhere();
              showMessage('success', t('account.signedOutOthers'));
            } catch (e) {
              showMessage('error', (e as Error).message);
              throw e;
            }
          }}
        >
          {t('account.signOutOthersBody')}
        </ConfirmModal>
      )}
    </>
  );
}
