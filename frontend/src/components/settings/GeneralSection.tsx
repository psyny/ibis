import { FormEvent, useMemo, useState } from 'react';
import { updateHousehold } from '../../api/households';
import type { Household } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';

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
  const [saving, setSaving] = useState(false);
  const showMessage = useMessage();

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
        ...(autoClose ? { auto_close_days: Math.max(0, Number(days) || 0) } : { disable_auto_close: true }),
      });
      showMessage('success', 'Settings saved');
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
        Household
      </h2>
      <div className="form-field">
        <label className="form-label" htmlFor="hh-name">
          Name
        </label>
        <input id="hh-name" className="form-input" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div className="form-grid form-grid--2">
        <div className="form-field">
          <label className="form-label" htmlFor="hh-currency">
            Currency
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
            Timezone
          </label>
          <input id="hh-tz" className="form-input" list="tz-list" value={timezone} onChange={(e) => setTimezone(e.target.value)} />
          <datalist id="tz-list">
            {timezones.map((tz) => (
              <option key={tz} value={tz} />
            ))}
          </datalist>
          <span className="form-hint">Decides when a new month starts.</span>
        </div>
      </div>
      <div className="form-field">
        <span className="form-label">Auto-close months</span>
        <label className="checkbox">
          <input type="checkbox" checked={autoClose} onChange={(e) => setAutoClose(e.target.checked)} />
          Close each month automatically
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
            <span className="muted">days after the month ends</span>
          </div>
        )}
      </div>
      <button className="button button--primary" disabled={saving}>
        {saving ? 'Saving...' : 'Save'}
      </button>
    </form>
  );
}
