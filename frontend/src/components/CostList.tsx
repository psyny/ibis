import { Link, useNavigate } from 'react-router-dom';
import type { Cost, MonthSummary } from '../api/types';
import { formatMoney, shortDate } from '../utils/format';

interface Props {
  householdId: string;
  summary: MonthSummary;
  /** Managers/admins get a delete button on each row (open months only) */
  onDelete?: (cost: Cost) => void;
}

/** The month's costs: cards on phones, a table on wider screens. Editable rows open the edit page. */
export function CostList({ householdId, summary, onDelete }: Props) {
  const navigate = useNavigate();
  const names = new Map(summary.members.map((m) => [m.id, m.display_name]));
  const colors = new Map(summary.categories.map((c) => [c.id, c.color]));
  const people = (ids: string[]) => ids.map((id) => names.get(id) || '?').join(', ');
  const money = (v: number) => formatMoney(v, summary.currency);
  const editUrl = (c: Cost) => `/h/${householdId}/costs/${c.id}`;
  const canDelete = !!onDelete && summary.can_manage && summary.month.status === 'open';
  const deleteButton = (c: Cost) =>
    canDelete && (
      <button
        type="button"
        className="row-delete"
        aria-label={`Delete ${c.description}`}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onDelete!(c);
        }}
      >
        Delete
      </button>
    );

  if (summary.costs.length === 0) {
    return (
      <div className="state-message">
        No costs this month.
        {summary.can_add_cost && <div className="state-message__sub">Tap “Add cost” below to add the first one.</div>}
      </div>
    );
  }

  const category = (c: Cost) =>
    c.category_name ? (
      <span className="tag">
        <span className="tag__dot" style={{ background: colors.get(c.category_id!) || '#6b6b6b' }} />
        {c.category_name}
      </span>
    ) : (
      <span className="muted small">—</span>
    );

  return (
    <>
      <div className="cost-list mobile-only">
        {summary.costs.map((c) => {
          const body = (
            <>
              <div className="cost-item__title">
                {c.description}
                {c.source === 'recurring' && <span className="muted small" title="Fixed cost"> ↻</span>}
              </div>
              <div className="cost-item__amount num">{money(c.amount)}</div>
              <div className="cost-item__meta">
                <span>{shortDate(c.date)}</span>
                {category(c)}
                {deleteButton(c)}
              </div>
              <div className="cost-item__share num">{money(c.cover_share)} each</div>
              <div className="cost-item__people">
                <span className="muted">Paid:</span> {people(c.payer_ids)} · <span className="muted">Covers:</span>{' '}
                {people(c.coverer_ids)}
              </div>
            </>
          );
          return c.can_edit ? (
            <Link key={c.id} to={editUrl(c)} className="cost-item">
              {body}
            </Link>
          ) : (
            <div key={c.id} className="cost-item">
              {body}
            </div>
          );
        })}
      </div>

      <div className="desktop-only">
        <table className="cost-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th>Category</th>
              <th className="num">Total</th>
              <th>Paid by</th>
              <th>Covered by</th>
              <th className="num">Each covers</th>
              {canDelete && <th aria-label="Actions" />}
            </tr>
          </thead>
          <tbody>
            {summary.costs.map((c) => (
              <tr
                key={c.id}
                className={c.can_edit ? 'cost-table__row--editable' : ''}
                onClick={c.can_edit ? () => navigate(editUrl(c)) : undefined}
                title={c.can_edit ? 'Edit' : undefined}
              >
                <td className="nowrap">{shortDate(c.date)}</td>
                <td>
                  {c.description}
                  {c.source === 'recurring' && <span className="muted small" title="Fixed cost"> ↻</span>}
                </td>
                <td>{category(c)}</td>
                <td className="num">{money(c.amount)}</td>
                <td>{people(c.payer_ids)}</td>
                <td>{people(c.coverer_ids)}</td>
                <td className="num">{money(c.cover_share)}</td>
                {canDelete && <td>{deleteButton(c)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
