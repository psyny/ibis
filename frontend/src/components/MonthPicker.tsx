import { useEffect, useState } from 'react';
import { listMonths } from '../api/households';
import type { MonthInfo } from '../api/types';
import { formatMoney, monthLabel } from '../utils/format';
import { Modal } from './Modal';

interface MonthPickerProps {
  householdId: string;
  currency: string;
  year: number;
  month: number;
  onPick: (year: number, month: number) => void;
  onClose: () => void;
}

export function MonthPicker({ householdId, currency, year, month, onPick, onClose }: MonthPickerProps) {
  const [months, setMonths] = useState<MonthInfo[] | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    listMonths(householdId)
      .then(setMonths)
      .catch((e: Error) => setError(e.message));
  }, [householdId]);

  return (
    <Modal title="Change month" onClose={onClose}>
      {error && <p className="form-error">{error}</p>}
      {!months && !error && <p className="muted">Loading months...</p>}
      {months && (
        <div className="month-list">
          {months.map((m) => (
            <button
              key={m.id}
              className={`month-option ${m.year === year && m.month === month ? 'month-option--current' : ''}`}
              onClick={() => onPick(m.year, m.month)}
            >
              <span>
                <strong>{monthLabel(m.year, m.month)}</strong>
                <span className="muted small"> · {m.cost_count} costs</span>
              </span>
              <span className="row">
                <span className="num small">{formatMoney(m.total, currency)}</span>
                <span className={`pill pill--${m.status}`}>{m.status === 'open' ? 'Open' : 'Closed'}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </Modal>
  );
}
