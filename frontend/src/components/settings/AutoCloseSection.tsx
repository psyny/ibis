import { FormEvent, useState } from 'react';
import { updateHousehold } from '../../api/households';
import type { Household } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
import { useI18n } from '../../i18n';

interface Props {
  household: Household;
  onSaved: () => void;
}

/** Settings -> Expenses -> Month close: close each month automatically N days after it ends. */
export function AutoCloseSection({ household, onSaved }: Props) {
  const [autoClose, setAutoClose] = useState(household.auto_close_days !== null);
  const [days, setDays] = useState(String(household.auto_close_days ?? 5));
  const [saving, setSaving] = useState(false);
  const showMessage = useMessage();
  const { t } = useI18n();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateHousehold(
        household.id,
        autoClose ? { auto_close_days: Math.max(0, Number(days) || 0) } : { disable_auto_close: true },
      );
      showMessage('success', t('general.saved'));
      onSaved();
    } catch (err) {
      showMessage('error', (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="card" onSubmit={submit}>
      <h2 className="card__title" style={{ marginBottom: 14 }}>
        {t('general.autoClose')}
      </h2>
      <div className="form-field">
        <label className="checkbox">
          <input type="checkbox" checked={autoClose} onChange={(e) => setAutoClose(e.target.checked)} />
          {t('general.autoCloseCheckbox')}
        </label>
        {autoClose && (
          <div className="row" style={{ marginTop: 8 }}>
            <input
              className="form-input"
              style={{ width: 90 }}
              type="number"
              min={0}
              max={365}
              inputMode="numeric"
              value={days}
              onChange={(e) => setDays(e.target.value)}
            />
            <span className="muted">{t('general.daysAfterEnd')}</span>
          </div>
        )}
      </div>
      <button className="button button--primary" disabled={saving}>
        {saving ? t('common.saving') : t('common.save')}
      </button>
    </form>
  );
}
