import { FormEvent, useMemo, useState } from 'react';
import { updateHousehold } from '../../api/households';
import type { Household } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
import { LanguageCode, LANGUAGES, useI18n } from '../../i18n';

interface Props {
  household: Household;
  onSaved: () => void;
}

/** Settings -> General: name, currency, timezone, language. Expense rules live under Expenses. */
export function GeneralSection({ household, onSaved }: Props) {
  const [name, setName] = useState(household.name);
  const [currency, setCurrency] = useState(household.currency);
  const [timezone, setTimezone] = useState(household.timezone);
  const [language, setLanguage] = useState<LanguageCode>(household.language as LanguageCode);
  const [saving, setSaving] = useState(false);
  const showMessage = useMessage();
  const { t } = useI18n();

  const timezones = useMemo(() => {
    const intl = Intl as unknown as { supportedValuesOf?: (key: string) => string[] };
    return intl.supportedValuesOf ? intl.supportedValuesOf('timeZone') : [];
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateHousehold(household.id, {
        name,
        currency: currency.toUpperCase(),
        timezone,
        language,
      });
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
        {t('general.household')}
      </h2>
      <div className="form-field">
        <label className="form-label" htmlFor="hh-name">
          {t('common.name')}
        </label>
        <input id="hh-name" className="form-input" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div className="form-grid form-grid--2">
        <div className="form-field">
          <label className="form-label" htmlFor="hh-currency">
            {t('general.currency')}
          </label>
          <input
            id="hh-currency"
            className="form-input"
            value={currency}
            maxLength={3}
            onChange={(e) => setCurrency(e.target.value.toUpperCase())}
            placeholder="BRL, USD, EUR..."
          />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="hh-tz">
            {t('general.timezone')}
          </label>
          <input id="hh-tz" className="form-input" list="tz-list" value={timezone} onChange={(e) => setTimezone(e.target.value)} />
          <datalist id="tz-list">
            {timezones.map((tz) => (
              <option key={tz} value={tz} />
            ))}
          </datalist>
          <span className="form-hint">{t('general.timezoneHint')}</span>
        </div>
      </div>
      <div className="form-field">
        <label className="form-label" htmlFor="hh-lang">
          {t('general.language')}
        </label>
        <select id="hh-lang" className="form-select" value={language} onChange={(e) => setLanguage(e.target.value as LanguageCode)}>
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
        <span className="form-hint">{t('general.languageHint')}</span>
      </div>
      <button className="button button--primary" disabled={saving}>
        {saving ? t('common.saving') : t('common.save')}
      </button>
    </form>
  );
}
