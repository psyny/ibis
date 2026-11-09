import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { applyRecurring, closeMonth, createMonth, listMonths, reopenMonth } from '../../api/households';
import type { MonthInfo } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
import { useI18n } from '../../i18n';
import { formatMoney, longDate, monthKey, monthLabel } from '../../utils/format';

interface Props {
  householdId: string;
  currency: string;
}

export function MonthsSection({ householdId, currency }: Props) {
  const [months, setMonths] = useState<MonthInfo[] | null>(null);
  const [newMonth, setNewMonth] = useState('');
  const showMessage = useMessage();
  const { t, tn } = useI18n();

  const load = useCallback(() => {
    listMonths(householdId)
      .then(setMonths)
      .catch((e: Error) => showMessage('error', e.message));
  }, [householdId, showMessage]);
  useEffect(load, [load]);

  const run = async (action: () => Promise<unknown>, success: string) => {
    try {
      await action();
      showMessage('success', success);
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  const create = (e: FormEvent) => {
    e.preventDefault();
    const [year, month] = newMonth.split('-').map(Number);
    if (!year || !month) return;
    run(() => createMonth(householdId, year, month), t('month.created', { month: monthLabel(year, month) })).then(() => setNewMonth(''));
  };

  const addStarting = async (m: MonthInfo) => {
    try {
      const { added } = await applyRecurring(householdId, m.year, m.month);
      showMessage('success', added ? tn('month.fixedAdded', added, { month: monthLabel(m.year, m.month) }) : t('month.fixedNone', { month: monthLabel(m.year, m.month) }));
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  return (
    <section className="card">
      <h2 className="card__title" style={{ marginBottom: 6 }}>
        {t('settings.tab.months')}
      </h2>
      <p className="muted small" style={{ marginBottom: 8 }}>
        {t('months.hint')}
      </p>
      <form className="row" onSubmit={create} style={{ marginBottom: 8 }}>
        <input
          type="month"
          className="form-input"
          style={{ maxWidth: 200 }}
          value={newMonth}
          onChange={(e) => setNewMonth(e.target.value)}
          aria-label={t('months.toCreate')}
        />
        <button className="button button--primary" disabled={!newMonth}>
          {t('months.create')}
        </button>
      </form>
      {!months && <p className="muted">{t('common.loading')}</p>}
      <div className="list">
        {months?.map((m) => (
          <div key={m.id} className="list-item">
            <div className="list-item__main">
              <div className="list-item__title">
                <Link to={`/h/${householdId}/costs?m=${monthKey(m.year, m.month)}`}>{monthLabel(m.year, m.month)}</Link>{' '}
                <span className={`pill pill--${m.status}`}>{m.status === 'open' ? t('month.open') : t('month.closed')}</span>
              </div>
              <div className="list-item__sub">
                {tn('month.costCount', m.cost_count)} · {formatMoney(m.total, currency)}
                {m.status === 'open' && m.auto_close_on && ` · ${t('month.autoCloses', { date: longDate(m.auto_close_on) })}`}
              </div>
            </div>
            {m.status === 'open' ? (
              <>
                <button className="button button--ghost button--small" onClick={() => addStarting(m)}>
                  {t('monthMenu.addFixed')}
                </button>
                <button
                  className="button button--secondary button--small"
                  onClick={() =>
                    window.confirm(`${t('month.closeConfirmTitle', { month: monthLabel(m.year, m.month) })} ${t('month.closeConfirmBody')}`) &&
                    run(() => closeMonth(householdId, m.year, m.month), t('month.closedToast', { month: monthLabel(m.year, m.month) }))
                  }
                >
                  {t('months.close')}
                </button>
              </>
            ) : (
              <button
                className="button button--secondary button--small"
                onClick={() => run(() => reopenMonth(householdId, m.year, m.month), t('month.reopened', { month: monthLabel(m.year, m.month) }))}
              >
                {t('months.reopen')}
              </button>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
