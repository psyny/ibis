import type { TaskLabel } from '../api/types';
import { useI18n } from '../i18n';

export interface TaskSettingsValue {
  warn_days: number;
  notify_expiring: boolean;
  notify_expired: boolean;
}

interface Props {
  value: TaskSettingsValue;
  onChange: (value: TaskSettingsValue) => void;
}

/** "Expiring" warning days and which due-date notifications go to the assignees (tasks and recurring tasks). */
export function TaskSettingsFields({ value, onChange }: Props) {
  const { t, tn } = useI18n();
  const set = (patch: Partial<TaskSettingsValue>) => onChange({ ...value, ...patch });

  return (
    <>
      <div className="form-field">
        <label className="form-label" htmlFor="task-warn">
          {t('task.warnDays')}
        </label>
        <div className="inline-field">
          <input
            id="task-warn"
            className="form-input inline-field__number"
            type="number"
            inputMode="numeric"
            min={0}
            max={365}
            value={value.warn_days}
            onChange={(e) => set({ warn_days: Math.min(365, Math.max(0, Number(e.target.value) || 0)) })}
          />
          <span>{t('task.daysBefore')}</span>
        </div>
        <span className="form-hint">{t('task.warnDaysHint')}</span>
      </div>
      <fieldset className="form-field form-fieldset">
        <legend className="form-label">{t('task.notifyOn')}</legend>
        <label className="checkbox">
          <input type="checkbox" checked={value.notify_expiring} onChange={(e) => set({ notify_expiring: e.target.checked })} />
          {tn('task.notifyExpiringHint', value.warn_days)}
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={value.notify_expired} onChange={(e) => set({ notify_expired: e.target.checked })} />
          {t('task.notifyExpiredHint')}
        </label>
      </fieldset>
    </>
  );
}

/** Single-choice chips from one household list (task categories or locations); tapping the selected one clears it. */
export function LabelChips({
  label,
  labels,
  value,
  onChange,
}: {
  label: string;
  labels: TaskLabel[];
  value: string | null;
  onChange: (id: string | null) => void;
}) {
  if (labels.length === 0) return null;
  return (
    <div className="form-field">
      <span className="form-label">{label}</span>
      <div className="chips" role="radiogroup" aria-label={label}>
        {labels.map((item) => (
          <button
            type="button"
            key={item.id}
            role="radio"
            aria-checked={value === item.id}
            className={`chip chip--small ${value === item.id ? 'chip--selected' : ''}`}
            onClick={() => onChange(value === item.id ? null : item.id)}
          >
            {item.name}
          </button>
        ))}
      </div>
    </div>
  );
}
