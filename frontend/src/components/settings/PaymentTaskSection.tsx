import { FormEvent, useState } from 'react';
import { updateHousehold } from '../../api/households';
import type { Household, PaymentTaskSettings } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
import { useI18n } from '../../i18n';
import { TaskSettingsFields, TaskSettingsValue, taskSettingsOf } from '../TaskSettingsFields';

interface Props {
  household: Household;
  onSaved: () => void;
}

/** Managers: the "pay" task each person who owes money gets when a month closes. */
export function PaymentTaskSection({ household, onSaved }: Props) {
  const { t } = useI18n();
  const showMessage = useMessage();
  const current = household.payment_task;
  const [enabled, setEnabled] = useState(current.enabled);
  const [dueDays, setDueDays] = useState(current.due_days);
  const [settings, setSettings] = useState<TaskSettingsValue>(taskSettingsOf(current));
  const [saving, setSaving] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const { is_private: _unused, ...task } = settings; // payment tasks are never private
    const payment_task: PaymentTaskSettings = { ...task, enabled, due_days: dueDays };
    setSaving(true);
    try {
      await updateHousehold(household.id, { payment_task });
      showMessage('success', t('paymentTask.saved'));
      onSaved();
    } catch (err) {
      showMessage('error', (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="card" onSubmit={submit}>
      <h2 className="card__title" style={{ marginBottom: 6 }}>
        {t('paymentTask.title')}
      </h2>
      <p className="muted small" style={{ marginBottom: 14 }}>
        {t('paymentTask.hint')}
      </p>
      <div className="form-field">
        <label className="checkbox">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          {t('paymentTask.enabled')}
        </label>
        {!enabled && <span className="form-hint">{t('paymentTask.offHint')}</span>}
      </div>
      {enabled && (
        <>
          <div className="form-field">
            <label className="form-label" htmlFor="payment-due">
              {t('paymentTask.due')}
            </label>
            <div className="inline-field">
              <input
                id="payment-due"
                className="form-input inline-field__number"
                type="number"
                inputMode="numeric"
                min={0}
                max={365}
                value={dueDays}
                onChange={(e) => setDueDays(Math.min(365, Math.max(0, Number(e.target.value) || 0)))}
              />
              <span>{t('paymentTask.daysAfterClose')}</span>
            </div>
          </div>
          <TaskSettingsFields value={settings} onChange={setSettings} showPrivate={false} />
        </>
      )}
      <button className="button button--primary" disabled={saving}>
        {saving ? t('common.saving') : t('common.save')}
      </button>
    </form>
  );
}
