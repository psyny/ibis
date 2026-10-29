import type { BankInfoType } from '../api/types';
import { parsePixKey } from '../utils/pixKey';

interface Props {
  idPrefix: string;
  type: BankInfoType;
  value: string;
  onTypeChange: (type: BankInfoType) => void;
  onValueChange: (value: string) => void;
}

/** Problem with the bank info that should block saving, or null. Empty is allowed. */
export function bankInfoError(type: BankInfoType, value: string): string | null {
  if (type !== 'pix' || !value.trim()) return null;
  const parsed = parsePixKey(value);
  return parsed.ok ? null : parsed.error;
}

/** What to store: the cleaned-up PIX key (e.g. "+5521993815159"), or the text as typed for "other". */
export function normalizeBankInfo(type: BankInfoType, value: string): string {
  if (type !== 'pix' || !value.trim()) return value.trim();
  const parsed = parsePixKey(value);
  return parsed.ok ? parsed.key : value.trim();
}

/** "Bank info": a PIX key (used to generate payment QR codes) or any other text. */
export function BankInfoFields({ idPrefix, type, value, onTypeChange, onValueChange }: Props) {
  const parsed = type === 'pix' && value.trim() ? parsePixKey(value) : null;

  return (
    <div className="form-field">
      <label className="form-label" htmlFor={`${idPrefix}-bank`}>
        Bank info
      </label>
      <div className="row" style={{ flexWrap: 'nowrap' }}>
        <select
          className="form-select"
          style={{ width: 'auto', flexShrink: 0 }}
          value={type}
          onChange={(e) => onTypeChange(e.target.value as BankInfoType)}
          aria-label="Bank info type"
        >
          <option value="pix">PIX</option>
          <option value="other">Other</option>
        </select>
        <input
          id={`${idPrefix}-bank`}
          className="form-input grow"
          value={value}
          onChange={(e) => onValueChange(e.target.value)}
          placeholder={type === 'pix' ? 'Phone, CPF, CNPJ, email or random key' : 'Bank, account, IBAN...'}
          autoCapitalize="none"
          autoCorrect="off"
          maxLength={255}
          aria-invalid={parsed ? !parsed.ok : undefined}
          aria-describedby={`${idPrefix}-bank-hint`}
        />
      </div>
      <span id={`${idPrefix}-bank-hint`} className="form-hint" aria-live="polite">
        {type !== 'pix' && 'Any text that tells people how to pay this person.'}
        {type === 'pix' && !parsed && 'Type it any way you like, e.g. (21) 99381-5159 or 529.982.247-25. Used to create PIX payment QR codes.'}
        {parsed?.ok && (
          <span className="positive">
            ✓ {parsed.label}: {parsed.key}
          </span>
        )}
        {parsed && !parsed.ok && <span className="negative">✕ {parsed.error}</span>}
      </span>
    </div>
  );
}
