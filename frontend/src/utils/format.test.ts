import { addDays, monthKey, parseAmount, parseMonthKey, shiftMonth } from './format';

describe('parseAmount', () => {
  it('accepts dot and comma decimals', () => {
    expect(parseAmount('12.50')).toBe(12.5);
    expect(parseAmount('12,50')).toBe(12.5);
    expect(parseAmount('1.234,56')).toBe(1234.56);
    expect(parseAmount('1,234.56')).toBe(1234.56);
    expect(parseAmount('R$ 30')).toBe(30);
    expect(parseAmount('')).toBeNaN();
  });
});

describe('months', () => {
  it('shifts across years', () => {
    expect(shiftMonth(2026, 12, 1)).toEqual({ year: 2027, month: 1 });
    expect(shiftMonth(2026, 1, -1)).toEqual({ year: 2025, month: 12 });
  });
  it('round-trips keys', () => {
    expect(parseMonthKey(monthKey(2026, 3))).toEqual({ year: 2026, month: 3 });
    expect(parseMonthKey('2026-13')).toBeNull();
  });
  it('adds days', () => {
    expect(addDays('2026-03-01', -1)).toBe('2026-02-28');
  });
});
