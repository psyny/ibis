import { describe, expect, it } from 'vitest';
import type { Task } from '../api/types';
import { daysBetween, dueText } from './tasks';

const t = (key: string, params?: Record<string, string | number>) => `${key}${params ? JSON.stringify(params) : ''}`;
const tn = (key: string, count: number) => `${key}#${count}`;
const i18n = { t, tn } as never;

const task = (due_date: string | null, status: Task['status'] = 'pending', warn_days = 3) =>
  ({ due_date, status, warn_days }) as Task;

describe('task due text', () => {
  it('counts whole days', () => {
    expect(daysBetween('2026-11-08', '2026-11-11')).toBe(3);
    expect(daysBetween('2026-03-28', '2026-03-30')).toBe(2); // across a DST change
    expect(daysBetween('2026-11-08', '2026-11-06')).toBe(-2);
  });

  it('describes how close the due date is', () => {
    expect(dueText(task(null), '2026-11-08', i18n)).toBe('task.noDue');
    expect(dueText(task('2026-11-08', 'expiring'), '2026-11-08', i18n)).toBe('task.dueToday');
    expect(dueText(task('2026-11-09', 'expiring'), '2026-11-08', i18n)).toBe('task.dueTomorrow');
    expect(dueText(task('2026-11-11', 'expiring'), '2026-11-08', i18n)).toBe('task.dueIn#3');
    expect(dueText(task('2026-11-06', 'overdue'), '2026-11-08', i18n)).toMatch(/^task.overdueBy#2 · /);
    // Beyond the warning window (or done): just the date
    expect(dueText(task('2026-11-20'), '2026-11-08', i18n)).toMatch(/^task.dueOn/);
    expect(dueText(task('2026-11-06', 'completed'), '2026-11-08', i18n)).toMatch(/^task.dueOn/);
  });
});
