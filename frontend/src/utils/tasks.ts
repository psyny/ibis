import type { Task } from '../api/types';
import type { useI18n } from '../i18n';
import { formatMoney, monthLabel, shortDate } from './format';
import { monthPaymentData } from './notifications';

type I18n = ReturnType<typeof useI18n>;

/** Whole days from `from` to `to` (ISO dates, no timezone shifts). */
export function daysBetween(from: string, to: string): number {
  const utc = (iso: string) => {
    const [y, m, d] = iso.split('-').map(Number);
    return Date.UTC(y, m - 1, d);
  };
  return Math.round((utc(to) - utc(from)) / 86_400_000);
}

/** The task's title in the interface language (month-close payment tasks are built from their data). */
export function taskTitle(task: Task, t: I18n['t']): string {
  const payment = monthPaymentData(task.kind, task.data);
  return payment
    ? t('task.monthPayment.title', { name: payment.to_name, amount: formatMoney(payment.amount, payment.currency) })
    : task.title;
}

export function taskDescription(task: Task, t: I18n['t']): string | null {
  const payment = monthPaymentData(task.kind, task.data);
  return payment ? t('task.monthPayment.description', { month: monthLabel(payment.year, payment.month) }) : task.description;
}

/** Short due-date text next to the status color, e.g. "Due in 2 days" or "Overdue by 1 day · Oct 28". */
export function dueText(task: Task, today: string, { t, tn }: Pick<I18n, 't' | 'tn'>): string {
  if (!task.due_date) return t('task.noDue');
  const date = shortDate(task.due_date);
  const days = daysBetween(today, task.due_date);
  if (task.status === 'completed' || days > task.warn_days) return t('task.dueOn', { date });
  if (days < 0) return `${tn('task.overdueBy', -days)} · ${date}`;
  if (days === 0) return t('task.dueToday');
  if (days === 1) return t('task.dueTomorrow');
  return tn('task.dueIn', days);
}
