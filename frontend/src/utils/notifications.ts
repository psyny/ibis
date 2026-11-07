import type { AppNotification } from '../api/types';
import type { useI18n } from '../i18n';
import { formatMoney, monthKey, monthLabel } from './format';

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

interface MonthPaymentData {
  year: number;
  month: number;
  to_member_id: string;
  to_name: string;
  amount: number;
  currency: string;
  household_name: string;
}

const isMonthPayment = (n: AppNotification): n is AppNotification & { data: MonthPaymentData } =>
  n.kind === 'month_payment' && typeof n.data.year === 'number' && typeof n.data.to_member_id === 'string';

/** Title and second line in the interface language (falls back to the server's English text). */
export function notificationText(n: AppNotification, t: T): { title: string; body: string | null } {
  if (isMonthPayment(n)) {
    const d = n.data;
    return {
      title: t('notif.monthPayment.title', { name: d.to_name, amount: formatMoney(d.amount, d.currency) }),
      body: t('notif.monthPayment.body', { month: monthLabel(d.year, d.month), household: d.household_name }),
    };
  }
  return { title: n.title, body: n.body };
}

/** Where clicking the notification goes, if anywhere. */
export function notificationLink(n: AppNotification): string | null {
  if (isMonthPayment(n) && n.household_id) {
    const params = new URLSearchParams({ m: monthKey(n.data.year, n.data.month), pay: n.data.to_member_id });
    return `/h/${n.household_id}?${params}`;
  }
  return null;
}
