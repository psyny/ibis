import type { AppNotification } from '../api/types';
import type { useI18n } from '../i18n';
import { formatMoney, longDate, monthKey, monthLabel } from './format';

type T = ReturnType<typeof useI18n>['t'];

const CHANGED_EVENT = 'ibis:notifications-changed';

/** Tell the top bar (and any open inbox) to reload, e.g. after closing a month or acting on a notification. */
export function notificationsChanged(): void {
  window.dispatchEvent(new Event(CHANGED_EVENT));
}

export function onNotificationsChanged(listener: () => void): () => void {
  window.addEventListener(CHANGED_EVENT, listener);
  return () => window.removeEventListener(CHANGED_EVENT, listener);
}

export interface MonthPaymentData {
  year: number;
  month: number;
  to_member_id: string;
  to_name: string;
  amount: number;
  currency: string;
  household_name: string;
}

/** Payment data of a month-close notification or task. */
export function monthPaymentData(kind: string, data: Record<string, unknown>): MonthPaymentData | null {
  return kind === 'month_payment' && typeof data.year === 'number' && typeof data.to_member_id === 'string'
    ? (data as unknown as MonthPaymentData)
    : null;
}

/** The costs screen with the payment sheet open for this transfer. */
export function paymentLink(householdId: string, d: MonthPaymentData): string {
  const params = new URLSearchParams({ m: monthKey(d.year, d.month), pay: d.to_member_id });
  return `/h/${householdId}/costs?${params}`;
}

const text = (value: unknown) => (typeof value === 'string' ? value : '');

/** Title and second line in the interface language (falls back to the server's English text). */
export function notificationText(n: AppNotification, t: T): { title: string; body: string | null } {
  const payment = monthPaymentData(n.kind, n.data);
  if (payment) {
    return {
      title: t('notif.monthPayment.title', { name: payment.to_name, amount: formatMoney(payment.amount, payment.currency) }),
      body: t('notif.monthPayment.body', { month: monthLabel(payment.year, payment.month), household: payment.household_name }),
    };
  }
  if ((n.kind === 'task_expiring' || n.kind === 'task_expired') && n.data.due_date) {
    const title = text(n.data.task_title);
    return {
      title: n.kind === 'task_expiring' ? t('notif.taskExpiring', { title }) : t('notif.taskExpired', { title }),
      body: t('notif.taskDue', { date: longDate(text(n.data.due_date)), household: text(n.data.household_name) }),
    };
  }
  return { title: n.title, body: n.body };
}

/** Where clicking the notification goes, if anywhere: its task, or (older notes) the payment sheet. */
export function notificationLink(n: AppNotification): string | null {
  if (!n.household_id) return null;
  if (n.task_id) return `/h/${n.household_id}/tasks?task=${n.task_id}`;
  const payment = monthPaymentData(n.kind, n.data);
  return payment ? paymentLink(n.household_id, payment) : null;
}
