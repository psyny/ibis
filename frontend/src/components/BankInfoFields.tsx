import type { BankInfoType } from '../api/types';
import { MessageKey, useI18n } from '../i18n';
import { parsePixKey, PixKeyErrorCode, PixKeyParams } from '../utils/pixKey';

interface Props {
  idPrefix: string;
  type: BankInfoType;
  value: string;
  onTypeChange: (type: BankInfoType) => void;
  onValueChange: (value: string) => void;
}

type Translate = (key: MessageKey, params?: Record<string, string | number>) => string;

/** A PIX key problem in the interface language. */
export function pixErrorText(t: Translate, code: PixKeyErrorCode, params: PixKeyParams): string {
  return t(`pix.error.${code}` as MessageKey, params);
}

/** Problem with the bank info that should block saving (translated), or null. Empty is allowed. */
export function bankInfoError(t: Translate, type: BankInfoType, value: string): string | null {
  if (type !== 'pix' || !value.trim()) return null;
  const parsed = parsePixKey(value);
  return parsed.ok ? null : pixErrorText(t, parsed.code, parsed.params);
}

/** What to store: the cleaned-up PIX key (e.g. "+5521993815159"), or the text as typed for "other". */
export function normalizeBankInfo(type: BankInfoType, value: string): string {
  if (type !== 'pix' || !value.trim()) return value.trim();
  const parsed = parsePixKey(value);
  return parsed.ok ? parsed.key : value.trim();
}

/** "Bank info": a PIX key (used to generate payment QR codes) or any other text. */
export function BankInfoFields({ idPrefix, type, value, onTypeChange, onValueChange }: Props) {
  const { t } = useI18n();
  const parsed = type === 'pix' && value.trim() ? parsePixKey(value) : null;

  return (
    <div className="form-field">
      <label className="form-label" htmlFor={`${idPrefix}-bank`}>
        {t('bank.label')}
      </label>
      <div className="row" style={{ flexWrap: 'nowrap' }}>
        <select
          className="form-select"
          style={{ width: 'auto', flexShrink: 0 }}
          value={type}
          onChange={(e) => onTypeChange(e.target.value as BankInfoType)}
          aria-label={t('bank.typeLabel')}
        >
          <option value="pix">{t('bank.pix')}</option>
          <option value="other">{t('bank.other')}</option>
        </select>
        <input
          id={`${idPrefix}-bank`}
          className="form-input grow"
          value={value}
          onChange={(e) => onValueChange(e.target.value)}
          placeholder={type === 'pix' ? t('bank.placeholderPix') : t('bank.placeholderOther')}
          autoCapitalize="none"
          autoCorrect="off"
          maxLength={255}
          aria-invalid={parsed ? !parsed.ok : undefined}
          aria-describedby={`${idPrefix}-bank-hint`}
        />
      </div>
      <span id={`${idPrefix}-bank-hint`} className="form-hint" aria-live="polite">
        {type !== 'pix' && t('bank.hintOther')}
        {type === 'pix' && !parsed && t('bank.hintPix')}
        {parsed?.ok && (
          <span className="positive">
            ✓ {t(`pix.kind.${parsed.kind}` as MessageKey)}: {parsed.key}
          </span>
        )}
        {parsed && !parsed.ok && <span className="negative">✕ {pixErrorText(t, parsed.code, parsed.params)}</span>}
      </span>
    </div>
  );
}
