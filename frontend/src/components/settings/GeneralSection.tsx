import { FormEvent, useMemo, useState } from 'react';
import { updateHousehold } from '../../api/households';
import type { Household } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
import { LanguageCode, LANGUAGES, useI18n } from '../../i18n';

interface Props {
  household: Household;
  onSaved: () => void;
}

export function GeneralSection({ household, onSaved }: Props) {
  const [name, setName] = useState(household.name);
  const [currency, setCurrency] = useState(household.currency);
  const [timezone, setTimezone] = useState(household.timezone);
  const [autoClose, setAutoClose] = useState(household.auto_close_days !== null);
  const [days, setDays] = useState(String(household.auto_close_days ?? 5));
  const [shield, setShield] = useState(household.shield_costs_from_guests);
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
        shield_costs_from_guests: shield,
        language,
        ...(autoClose ? { auto_close_days: Math.max(0, Number(days) || 0) } : { disable_auto_close: true }),
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
      <div className="form-field">
        <span className="form-label">{t('general.autoClose')}</span>
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
      <div className="form-field">
        <span className="form-label">{t('general.privacy')}</span>
        <label className="checkbox">
          <input type="checkbox" checked={shield} onChange={(e) => setShield(e.target.checked)} />
          {t('general.shield')}
        </label>
        <span className="form-hint">
          {t('general.shieldHint')}
        </span>
      </div>
      <button className="button button--primary" disabled={saving}>
        {saving ? t('common.saving') : t('common.save')}
      </button>
    </form>
  );
}
