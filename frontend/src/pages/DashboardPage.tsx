import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ApiError } from '../api/config';
import { applyRecurring, closeMonth, createMonth, deleteCost, getMonthSummary, reopenMonth } from '../api/households';
import type { Cost, MonthSummary, Transfer } from '../api/types';
import { CategoryChart } from '../components/CategoryChart';
import { ConfirmModal } from '../components/ConfirmModal';
import { PixPayModal } from '../components/PixPayModal';
import { CostList } from '../components/CostList';
import { MemberContactModal } from '../components/MemberContactModal';
import { MonthActionsMenu } from '../components/MonthActionsMenu';
import { MonthPicker } from '../components/MonthPicker';
import { SplitCard } from '../components/SplitCard';
import { TopBar } from '../components/TopBar';
import { useMessage } from '../contexts/MessageContext';
import { useHousehold } from '../hooks/useHousehold';
import { formatMoney, monthKey, monthLabel, parseMonthKey, shiftMonth } from '../utils/format';

export function DashboardPage() {
  const { householdId } = useParams();
  const [params, setParams] = useSearchParams();
  const { household, error: householdError } = useHousehold(householdId);
  const [summary, setSummary] = useState<MonthSummary | null>(null);
  const [missingMonth, setMissingMonth] = useState(false);
  const [error, setError] = useState('');
  const [pickerOpen, setPickerOpen] = useState(false);
  const [contactId, setContactId] = useState<string | null>(null);
  const [paying, setPaying] = useState<Transfer | null>(null);
  const [deleting, setDeleting] = useState<Cost | null>(null);
  const [confirmClose, setConfirmClose] = useState(false);
  const showMessage = useMessage();

  // The current month (in the household's timezone) unless ?m=YYYY-MM says otherwise
  const today = household?.today;
  const fromUrl = parseMonthKey(params.get('m'));
  const current = today ? { year: Number(today.slice(0, 4)), month: Number(today.slice(5, 7)) } : null;
  const selected = fromUrl || current;
  const isCurrentMonth = !!selected && !!current && selected.year === current.year && selected.month === current.month;

  const load = useCallback(async () => {
    if (!householdId || !selected) return;
    setError('');
    setMissingMonth(false);
    try {
      setSummary(await getMonthSummary(householdId, selected.year, selected.month));
    } catch (e) {
      setSummary(null);
      if (e instanceof ApiError && e.status === 404) setMissingMonth(true);
      else setError((e as Error).message);
    }
  }, [householdId, selected?.year, selected?.month]);

  useEffect(() => {
    load();
  }, [load]);

  const goToMonth = (year: number, month: number) => {
    setPickerOpen(false);
    const isToday = current && current.year === year && current.month === month;
    setParams(isToday ? {} : { m: monthKey(year, month) });
  };

  const handleCreateMonth = async () => {
    if (!householdId || !selected) return;
    try {
      await createMonth(householdId, selected.year, selected.month);
      showMessage('success', `${monthLabel(selected.year, selected.month)} created`);
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  const handleReopen = async () => {
    if (!householdId || !summary) return;
    try {
      await reopenMonth(householdId, summary.month.year, summary.month.month);
      showMessage('success', `${monthLabel(summary.month.year, summary.month.month)} reopened`);
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  const handleAddFixedCosts = async () => {
    if (!householdId || !summary) return;
    const label = monthLabel(summary.month.year, summary.month.month);
    try {
      const { added } = await applyRecurring(householdId, summary.month.year, summary.month.month);
      showMessage(
        'success',
        added ? `Added ${added} fixed cost${added > 1 ? 's' : ''} to ${label}` : `All fixed costs are already in ${label}`,
      );
      if (added) load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  if (householdError) {
    return (
      <>
        <TopBar />
        <div className="page">
          <div className="page__inner page__inner--narrow">
            <div className="card state-message">{householdError}</div>
          </div>
        </div>
      </>
    );
  }

  const addUrl =
    householdId && selected
      ? `/h/${householdId}/add${isCurrentMonth ? '' : `?date=${monthKey(selected.year, selected.month)}-01`}`
      : '#';

  return (
    <>
      <TopBar householdId={householdId} householdName={household?.name} canManage={household?.permissions.can_manage}>
        {selected && (
          <div className="topbar__month">
            <button
              className="icon-button topbar__month-arrow"
              aria-label="Previous month"
              onClick={() => {
                const p = shiftMonth(selected.year, selected.month, -1);
                goToMonth(p.year, p.month);
              }}
            >
              ‹
            </button>
            <button className="topbar__month-label" onClick={() => setPickerOpen(true)} title="Change month">
              {monthLabel(selected.year, selected.month, 'short')}
            </button>
            <button
              className="icon-button topbar__month-arrow"
              aria-label="Next month"
              onClick={() => {
                const n = shiftMonth(selected.year, selected.month, 1);
                goToMonth(n.year, n.month);
              }}
            >
              ›
            </button>
          </div>
        )}
        {summary && summary.can_manage && (
          <MonthActionsMenu
            month={summary.month}
            onClose={() => setConfirmClose(true)}
            onReopen={handleReopen}
            onAddFixedCosts={handleAddFixedCosts}
          />
        )}
      </TopBar>

      <main className="page">
        <div className="page__inner">
          {!household && <div className="state-message">Loading...</div>}
          {error && <div className="card state-message form-error">{error}</div>}

          {missingMonth && selected && (
            <div className="card state-message">
              {monthLabel(selected.year, selected.month)} has not been created yet.
              {household?.permissions.can_manage ? (
                <div style={{ marginTop: 16 }}>
                  <button className="button button--primary" onClick={handleCreateMonth}>
                    Create {monthLabel(selected.year, selected.month)}
                  </button>
                </div>
              ) : (
                <div className="state-message__sub">A manager can create it.</div>
              )}
              {!isCurrentMonth && (
                <div style={{ marginTop: 12 }}>
                  <button className="button button--ghost" onClick={() => setParams({})}>
                    Back to the current month
                  </button>
                </div>
              )}
            </div>
          )}

          {summary && household && (
            <>
              {summary.month.status === 'closed' && (
                <div className="banner banner--warning">
                  {monthLabel(summary.month.year, summary.month.month)} is closed. Costs can't be added or changed.
                </div>
              )}
              {summary.month.status === 'open' && summary.month.auto_close_on && (
                <p className="muted small">
                  Closes automatically on {new Date(summary.month.auto_close_on + 'T00:00').toLocaleDateString()}
                </p>
              )}

              <SplitCard summary={summary} onPersonClick={setContactId} onPayClick={setPaying} />

              <section className="card" aria-labelledby="categories-title">
                <div className="card__header">
                  <h2 className="card__title" id="categories-title">
                    By category
                  </h2>
                  <span className="card__subtitle num">{formatMoney(summary.total, summary.currency)}</span>
                </div>
                <CategoryChart totals={summary.category_totals} total={summary.total} currency={summary.currency} />
              </section>

              <section className="card" aria-labelledby="costs-title">
                <div className="card__header">
                  <h2 className="card__title" id="costs-title">
                    Costs
                  </h2>
                  <span className="card__subtitle">
                    {summary.costs.length} · {formatMoney(summary.total, summary.currency)}
                  </span>
                </div>
                <CostList householdId={household.id} summary={summary} onDelete={setDeleting} />
              </section>

              <div className="page-actions">
                {summary.can_add_cost && (
                  <Link to={addUrl} className="button button--primary button--large">
                    + Add cost
                  </Link>
                )}
              </div>
            </>
          )}
        </div>
      </main>

      {confirmClose && summary && householdId && (
        <ConfirmModal
          title={`Close ${monthLabel(summary.month.year, summary.month.month)}?`}
          confirmLabel="Close month"
          onClose={() => setConfirmClose(false)}
          onConfirm={async () => {
            try {
              await closeMonth(householdId, summary.month.year, summary.month.month);
              showMessage('success', `${monthLabel(summary.month.year, summary.month.month)} closed`);
              load();
            } catch (e) {
              showMessage('error', (e as Error).message);
              throw e;
            }
          }}
        >
          Nobody will be able to add, change or delete costs in this month. A manager can reopen it later.
        </ConfirmModal>
      )}
      {deleting && householdId && summary && (
        <ConfirmModal
          title="Delete this cost?"
          confirmLabel="Delete"
          danger
          onClose={() => setDeleting(null)}
          onConfirm={async () => {
            try {
              await deleteCost(householdId, deleting.id);
              showMessage('success', `Deleted ${deleting.description}`);
              load();
            } catch (e) {
              showMessage('error', (e as Error).message);
              throw e;
            }
          }}
        >
          {deleting.description} · {formatMoney(deleting.amount, summary.currency)}
        </ConfirmModal>
      )}
      {paying && summary && householdId && summary.members.some((m) => m.id === paying.to_member_id) && (
        <PixPayModal
          householdId={householdId}
          payerName={summary.members.find((m) => m.id === paying.from_member_id)?.display_name || ''}
          receiver={summary.members.find((m) => m.id === paying.to_member_id)!}
          amount={paying.amount}
          currency={summary.currency}
          onClose={() => setPaying(null)}
        />
      )}

      {pickerOpen && household && selected && (
        <MonthPicker
          householdId={household.id}
          currency={household.currency}
          year={selected.year}
          month={selected.month}
          onPick={goToMonth}
          onClose={() => setPickerOpen(false)}
        />
      )}
      {contactId && householdId && (
        <MemberContactModal householdId={householdId} memberId={contactId} onClose={() => setContactId(null)} />
      )}
    </>
  );
}
