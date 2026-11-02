const formatters = new Map<string, Intl.NumberFormat>();

export function formatMoney(amount: number, currency: string): string {
  let formatter = formatters.get(currency);
  if (!formatter) {
    try {
      formatter = new Intl.NumberFormat(undefined, { style: 'currency', currency });
    } catch {
      formatter = new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    formatters.set(currency, formatter);
  }
  return formatter.format(amount);
}

export function monthLabel(year: number, month: number, style: 'long' | 'short' = 'long'): string {
  return new Date(year, month - 1, 1).toLocaleDateString(undefined, { month: style, year: 'numeric' });
}

/** "2026-10" <-> {year, month} */
export function monthKey(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, '0')}`;
}

export function parseMonthKey(key: string | null | undefined): { year: number; month: number } | null {
  const match = key?.match(/^(\d{4})-(\d{1,2})$/);
  if (!match) return null;
  const month = Number(match[2]);
  if (month < 1 || month > 12) return null;
  return { year: Number(match[1]), month };
}

export function shiftMonth(year: number, month: number, delta: number): { year: number; month: number } {
  const index = year * 12 + (month - 1) + delta;
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

/** ISO date "2026-10-28" -> { year: 2026, month: 10 } */
export function monthOfDate(iso: string): { year: number; month: number } {
  return { year: Number(iso.slice(0, 4)), month: Number(iso.slice(5, 7)) };
}

/** Last day of a month as an ISO date, e.g. (2026, 2) -> "2026-02-28" */
export function lastDayOfMonth(year: number, month: number): string {
  const day = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

/** ISO date "2026-10-28" -> "Oct 28" (no timezone shifts) */
export function shortDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(Date.UTC(y, m - 1, d + days));
  return date.toISOString().slice(0, 10);
}

/** Accepts "12.50", "12,50", "1.234,56", "1,234.56". Returns NaN if not a number. */
export function parseAmount(raw: string): number {
  let value = raw.trim().replace(/[^\d.,-]/g, '');
  if (!value) return NaN;
  const lastComma = value.lastIndexOf(',');
  const lastDot = value.lastIndexOf('.');
  if (lastComma > lastDot) {
    value = value.replace(/\./g, '').replace(',', '.');
  } else {
    value = value.replace(/,/g, '');
  }
  return Number(value);
}

export const ROLE_LABELS: Record<string, string> = {
  manager: 'Manager',
  resident: 'Resident',
  guest: 'Guest',
  viewer: 'Viewer',
};
