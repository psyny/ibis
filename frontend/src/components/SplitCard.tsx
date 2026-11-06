import { useState } from 'react';
import type { MonthSummary, Transfer } from '../api/types';
import { useI18n } from '../i18n';
import { formatMoney } from '../utils/format';

interface Props {
  summary: MonthSummary;
  /** The logged-in user's member id, used to color their transfers once the month is closed */
  myMemberId: string | null;
  onPersonClick: (memberId: string) => void;
  /** Tapping a transfer opens the payment (PIX) sheet */
  onPayClick: (transfer: Transfer) => void;
}

/** Who pays whom (fewest transfers), plus per-person paid/covered details. */
export function SplitCard({ summary, myMemberId, onPersonClick, onPayClick }: Props) {
  const [showDetails, setShowDetails] = useState(false);
  const { t, tn } = useI18n();
  const names = new Map(summary.members.map((m) => [m.id, m.display_name]));
  const name = (id: string) => names.get(id) || t('split.unknown');
  const money = (v: number) => formatMoney(v, summary.currency);
  const closed = summary.month.status === 'closed';

  const rowTone = (tr: Transfer) => {
    if (!closed || !myMemberId) return '';
    if (tr.to_member_id === myMemberId) return ' split-row--receive';
    if (tr.from_member_id === myMemberId) return ' split-row--pay';
    return '';
  };

  const person = (id: string) => (
    <button
      className="person-link"
      onClick={(e) => {
        e.stopPropagation(); // the row itself opens the payment sheet
        onPersonClick(id);
      }}
      onKeyDown={(e) => e.stopPropagation()}
      title={t('split.personTitle')}
    >
      {name(id)}
    </button>
  );

  return (
    <section className="card" aria-labelledby="split-title">
      <div className="card__header">
        <h2 className="card__title" id="split-title">
          {t('split.title')}
        </h2>
        <span className="card__subtitle">
          {summary.restricted ? t('split.yourTransfers') : tn('split.settleCount', summary.transfers.length)}
        </span>
      </div>

      {summary.transfers.length === 0 ? (
        <p className="muted">
          {summary.costs.length === 0 ? t('split.noCosts') : summary.restricted ? t('split.youEven') : t('split.allEven')}
        </p>
      ) : (
        <>
          <div className="split-list">
            {summary.transfers.map((tr) => (
              // A div with button role, because the row holds the name buttons (buttons can't nest)
              <div
                className={`split-row${rowTone(tr)}`}
                key={`${tr.from_member_id}-${tr.to_member_id}`}
                role="button"
                tabIndex={0}
                onClick={() => onPayClick(tr)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onPayClick(tr);
                  }
                }}
                title={t('split.payTitle', { name: name(tr.to_member_id) })}
              >
                <div className="split-row__people">
                  {person(tr.from_member_id)}
                  <span className="split-row__arrow">{t('split.pays')}</span>
                  {person(tr.to_member_id)}
                </div>
                <span className="split-row__amount num">{money(tr.amount)}</span>
              </div>
            ))}
          </div>
          <p className="muted small" style={{ marginTop: 8 }}>
            {t('split.hint')}
          </p>
        </>
      )}

      {summary.balances.length > 0 && (
        <>
          <button className="button button--ghost button--small details-toggle" onClick={() => setShowDetails((v) => !v)}>
            {showDetails ? t('split.hideDetails') : t('split.showDetails')}
          </button>
          {showDetails && (
            <table className="balances-table">
              <thead>
                <tr>
                  <th>{t('split.col.person')}</th>
                  <th>{t('split.col.paid')}</th>
                  <th>{t('split.col.covers')}</th>
                  <th>{t('split.col.balance')}</th>
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
