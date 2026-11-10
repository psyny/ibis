import type { TaskLabel } from '../api/types';
import { MessageKey, useI18n } from '../i18n';

export interface TaskSettingsValue {
  warn_days: number;
  notify_expiring: boolean;
  notify_expired: boolean;
  notify_expiring_whatsapp: boolean;
  notify_expiring_email: boolean;
  notify_expiring_groups: boolean;
  notify_expired_whatsapp: boolean;
  notify_expired_email: boolean;
  notify_expired_groups: boolean;
  is_private: boolean;
}

/** The form's starting values from a task or recurring task (or the defaults for a new one). */
export function taskSettingsOf(source?: Partial<TaskSettingsValue> | null): TaskSettingsValue {
  return {
    warn_days: source?.warn_days ?? 3,
    notify_expiring: source?.notify_expiring ?? false,
    notify_expired: source?.notify_expired ?? false,
    notify_expiring_whatsapp: source?.notify_expiring_whatsapp ?? false,
    notify_expiring_email: source?.notify_expiring_email ?? false,
    notify_expiring_groups: source?.notify_expiring_groups ?? false,
    notify_expired_whatsapp: source?.notify_expired_whatsapp ?? false,
    notify_expired_email: source?.notify_expired_email ?? false,
    notify_expired_groups: source?.notify_expired_groups ?? false,
    is_private: source?.is_private ?? false,
  };
}

type Event = 'expiring' | 'expired';
type Channel = '' | '_whatsapp' | '_groups' | '_email';
const CHANNELS: { suffix: Channel; label: MessageKey }[] = [
  { suffix: '', label: 'task.notify.app' },
  { suffix: '_whatsapp', label: 'task.notify.whatsapp' },
  { suffix: '_groups', label: 'task.notify.groups' },
  { suffix: '_email', label: 'task.notify.email' },
];
const flag = (event: Event, suffix: Channel) => `notify_${event}${suffix}` as keyof TaskSettingsValue;

/** Which notifications the active ones are, for the task details (e.g. "About to expire: App, WhatsApp"). */
export function notifySummary(value: TaskSettingsValue, t: ReturnType<typeof useI18n>['t']): string[] {
  return (['expiring', 'expired'] as Event[]).flatMap((event) => {
    const on = CHANNELS.filter((c) => value[flag(event, c.suffix)]).map((c) => t(c.label));
    return on.length ? [`${t(event === 'expiring' ? 'task.notifyExpiring' : 'task.notifyExpired')}: ${on.join(', ')}`] : [];
  });
}

interface Props {
  value: TaskSettingsValue;
  onChange: (value: TaskSettingsValue) => void;
}

/** "Expiring" warning days, who gets notified (app, WhatsApp, groups, email) and the Private flag.
 * Shared by tasks and recurring tasks. */
export function TaskSettingsFields({ value, onChange }: Props) {
  const { t, tn } = useI18n();
  const set = (patch: Partial<TaskSettingsValue>) => onChange({ ...value, ...patch });

  const group = (event: Event, legend: string) => (
    <div className="notify-group">
      <span className="notify-group__title">{legend}</span>
      <div className="notify-group__options">
        {CHANNELS.map(({ suffix, label }) => {
          const key = flag(event, suffix);
          return (
            <label key={suffix} className="checkbox">
              <input type="checkbox" checked={value[key] as boolean} onChange={(e) => set({ [key]: e.target.checked })} />
              {t(label)}
              {suffix === '_email' && <span className="pill pill--muted">{t('task.notify.soon')}</span>}
            </label>
          );
        })}
      </div>
    </div>
  );

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
        <legend className="form-label">{t('task.notify.title')}</legend>
        {group('expiring', tn('task.notifyExpiringHint', value.warn_days))}
        {group('expired', t('task.notifyExpiredHint'))}
        <span className="form-hint">{t('task.notify.hint')}</span>
      </fieldset>
      <div className="form-field">
        <label className="checkbox">
          <input type="checkbox" checked={value.is_private} onChange={(e) => set({ is_private: e.target.checked })} />
          {t('task.private')}
        </label>
        <span className="form-hint">{t('task.privateHint')}</span>
      </div>
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
