import { FormEvent, useState } from 'react';
import { updateHousehold } from '../../api/households';
import type { Household } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
import { useI18n } from '../../i18n';

interface Props {
  household: Household;
  onSaved: () => void;
}

/** Settings -> Expenses -> General: who sees which costs. */
export function ExpensesGeneralSection({ household, onSaved }: Props) {
  const [shield, setShield] = useState(household.shield_costs_from_guests);
  const [saving, setSaving] = useState(false);
  const showMessage = useMessage();
  const { t } = useI18n();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateHousehold(household.id, { shield_costs_from_guests: shield });
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
        {t('general.privacy')}
      </h2>
      <div className="form-field">
        <label className="checkbox">
          <input type="checkbox" checked={shield} onChange={(e) => setShield(e.target.checked)} />
          {t('general.shield')}
        </label>
        <span className="form-hint">{t('general.shieldHint')}</span>
      </div>
      <button className="button button--primary" disabled={saving}>
        {saving ? t('common.saving') : t('common.save')}
      </button>
    </form>
  );
}
