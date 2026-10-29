import { useState } from 'react';
import type { MonthSummary, Transfer } from '../api/types';
import { formatMoney } from '../utils/format';

interface Props {
  summary: MonthSummary;
  onPersonClick: (memberId: string) => void;
  /** Tapping an amount opens the payment (PIX) sheet */
  onPayClick: (transfer: Transfer) => void;
}

/** Who pays whom (fewest transfers), plus per-person paid/covered details. */
export function SplitCard({ summary, onPersonClick, onPayClick }: Props) {
  const [showDetails, setShowDetails] = useState(false);
  const names = new Map(summary.members.map((m) => [m.id, m.display_name]));
  const name = (id: string) => names.get(id) || 'Unknown';
  const money = (v: number) => formatMoney(v, summary.currency);

  const person = (id: string) => (
    <button className="person-link" onClick={() => onPersonClick(id)} title="See contact and payment info">
      {name(id)}
    </button>
  );

  return (
    <section className="card" aria-labelledby="split-title">
      <div className="card__header">
        <h2 className="card__title" id="split-title">
          Split
        </h2>
        <span className="card__subtitle">
          {summary.restricted
            ? 'Your transfers'
            : `${summary.transfers.length === 1 ? '1 transfer' : `${summary.transfers.length} transfers`} settle everything`}
        </span>
      </div>

      {summary.transfers.length === 0 ? (
        <p className="muted">
          {summary.costs.length === 0 ? 'No costs yet this month.' : summary.restricted ? "You're even. 🎉" : 'Everyone is even. 🎉'}
        </p>
      ) : (
        <>
          <div className="split-list">
            {summary.transfers.map((t) => (
              <div className="split-row" key={`${t.from_member_id}-${t.to_member_id}`}>
                <div className="split-row__people">
                  {person(t.from_member_id)}
                  <span className="split-row__arrow">pays →</span>
                  {person(t.to_member_id)}
                </div>
                <button
                  className="split-row__amount num"
                  onClick={() => onPayClick(t)}
                  title={`Pay ${name(t.to_member_id)} (PIX)`}
                >
                  {money(t.amount)}
                </button>
              </div>
            ))}
          </div>
          <p className="muted small" style={{ marginTop: 8 }}>
            Tap an amount to pay it with PIX. Tap a name for contact info.
          </p>
        </>
      )}

      {summary.balances.length > 0 && (
        <>
          <button className="button button--ghost button--small details-toggle" onClick={() => setShowDetails((v) => !v)}>
            {showDetails ? 'Hide' : 'Show'} who paid and covered what
          </button>
          {showDetails && (
            <table className="balances-table">
              <thead>
                <tr>
                  <th>Person</th>
                  <th>Paid</th>
                  <th>Covers</th>
                  <th>Balance</th>
                </tr>
              </thead>
              <tbody>
                {summary.balances.map((b) => (
                  <tr key={b.member_id}>
                    <td>{person(b.member_id)}</td>
                    <td className="num">{money(b.paid)}</td>
                    <td className="num">{money(b.covered)}</td>
                    <td className={`num ${b.net > 0 ? 'positive' : b.net < 0 ? 'negative' : ''}`}>
                      {b.net > 0 ? '+' : ''}
                      {money(b.net)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  );
}
