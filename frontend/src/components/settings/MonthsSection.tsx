import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { applyRecurring, closeMonth, createMonth, listMonths, reopenMonth } from '../../api/households';
import type { MonthInfo } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
import { formatMoney, monthKey, monthLabel } from '../../utils/format';

interface Props {
  householdId: string;
  currency: string;
}

export function MonthsSection({ householdId, currency }: Props) {
  const [months, setMonths] = useState<MonthInfo[] | null>(null);
  const [newMonth, setNewMonth] = useState('');
  const showMessage = useMessage();

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
    run(() => createMonth(householdId, year, month), `${monthLabel(year, month)} created`).then(() => setNewMonth(''));
  };

  const addStarting = async (m: MonthInfo) => {
    try {
      const { added } = await applyRecurring(householdId, m.year, m.month);
      showMessage('success', added ? `Added ${added} fixed cost${added > 1 ? 's' : ''}` : 'Nothing missing: all fixed costs are already there');
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  return (
    <section className="card">
      <h2 className="card__title" style={{ marginBottom: 6 }}>
        Months
      </h2>
      <p className="muted small" style={{ marginBottom: 8 }}>
        The current and next month are created automatically. A closed month accepts no new or changed costs.
      </p>
      <form className="row" onSubmit={create} style={{ marginBottom: 8 }}>
        <input
          type="month"
          className="form-input"
          style={{ maxWidth: 200 }}
          value={newMonth}
          onChange={(e) => setNewMonth(e.target.value)}
          aria-label="Month to create"
        />
        <button className="button button--primary" disabled={!newMonth}>
          Create month
        </button>
      </form>
      {!months && <p className="muted">Loading...</p>}
      <div className="list">
        {months?.map((m) => (
          <div key={m.id} className="list-item">
            <div className="list-item__main">
              <div className="list-item__title">
                <Link to={`/h/${householdId}?m=${monthKey(m.year, m.month)}`}>{monthLabel(m.year, m.month)}</Link>{' '}
                <span className={`pill pill--${m.status}`}>{m.status === 'open' ? 'Open' : 'Closed'}</span>
              </div>
              <div className="list-item__sub">
                {m.cost_count} costs · {formatMoney(m.total, currency)}
                {m.status === 'open' && m.auto_close_on && ` · auto-closes ${new Date(m.auto_close_on + 'T00:00').toLocaleDateString()}`}
              </div>
            </div>
            {m.status === 'open' ? (
              <>
                <button className="button button--ghost button--small" onClick={() => addStarting(m)}>
                  Add fixed costs
                </button>
                <button
                  className="button button--secondary button--small"
                  onClick={() =>
                    window.confirm(`Close ${monthLabel(m.year, m.month)}? No costs can be added or changed after that.`) &&
                    run(() => closeMonth(householdId, m.year, m.month), `${monthLabel(m.year, m.month)} closed`)
                  }
                >
                  Close
                </button>
              </>
            ) : (
              <button
                className="button button--secondary button--small"
                onClick={() => run(() => reopenMonth(householdId, m.year, m.month), `${monthLabel(m.year, m.month)} reopened`)}
              >
                Reopen
              </button>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
