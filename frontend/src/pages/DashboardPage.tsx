import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ApiError } from '../api/config';
import { applyRecurring, closeMonth, createMonth, deleteCost, getMonthSummary, listMonths, reopenMonth } from '../api/households';
import type { Cost, MonthSummary, Transfer } from '../api/types';
import { CategoryChart } from '../components/CategoryChart';
import { ConfirmModal } from '../components/ConfirmModal';
import { memberAsReceiver } from '../components/pixReceivers';
import { PixPayModal } from '../components/PixPayModal';
import { CostList } from '../components/CostList';
import { MemberContactModal } from '../components/MemberContactModal';
import { MonthActionsMenu } from '../components/MonthActionsMenu';
import { MonthPicker } from '../components/MonthPicker';
import { SplitCard } from '../components/SplitCard';
import { TopBar } from '../components/TopBar';
import { useMessage } from '../contexts/MessageContext';
import { useHousehold } from '../hooks/useHousehold';
import { useI18n } from '../i18n';
import { formatMoney, longDate, monthKey, monthLabel, monthOfDate, parseMonthKey, shiftMonth } from '../utils/format';

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
  const { t, tn } = useI18n();

  // Which month to show: ?m=YYYY-MM if given, otherwise the default month: last month while it is
  // still open (month transitions), else the current month (in the household's timezone).
  const today = household?.today;
  const fromUrl = parseMonthKey(params.get('m'));
  const current = today ? monthOfDate(today) : null;
  const [defaultMonth, setDefaultMonth] = useState<{ year: number; month: number } | null>(null);

  useEffect(() => {
    if (!householdId || !today) return;
    const cur = monthOfDate(today);
    const prev = shiftMonth(cur.year, cur.month, -1);
    let cancelled = false;
    listMonths(householdId)
      .then((months) => {
        const prevOpen = months.some((m) => m.year === prev.year && m.month === prev.month && m.status === 'open');
        if (!cancelled) setDefaultMonth(prevOpen ? prev : cur);
      })
      .catch(() => !cancelled && setDefaultMonth(cur));
    return () => {
      cancelled = true;
    };
  }, [householdId, today]);

  const sameMonth = (a: { year: number; month: number } | null, b: { year: number; month: number } | null) =>
    !!a && !!b && a.year === b.year && a.month === b.month;
  const selected = fromUrl || defaultMonth;
  const isDefaultMonth = sameMonth(selected, defaultMonth);
  const isCurrentMonth = sameMonth(selected, current);
  const showingOpenLastMonth = !fromUrl && !!defaultMonth && !sameMonth(defaultMonth, current);

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
    setParams(sameMonth({ year, month }, defaultMonth) ? {} : { m: monthKey(year, month) });
  };

  const handleCreateMonth = async () => {
    if (!householdId || !selected) return;
    try {
      await createMonth(householdId, selected.year, selected.month);
      showMessage('success', t('month.created', { month: monthLabel(selected.year, selected.month) }));
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  const handleReopen = async () => {
    if (!householdId || !summary) return;
    try {
      await reopenMonth(householdId, summary.month.year, summary.month.month);
      showMessage('success', t('month.reopened', { month: monthLabel(summary.month.year, summary.month.month) }));
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
        added ? tn('month.fixedAdded', added, { month: label }) : t('month.fixedNone', { month: label }),
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
      ? // The default month needs no date: the add screen picks the same default (open last month, else today)
        `/h/${householdId}/add${
          isDefaultMonth ? '' : `?date=${isCurrentMonth && today ? today : `${monthKey(selected.year, selected.month)}-01`}`
        }`
      : '#';

  return (
    <>
      <TopBar householdId={householdId} householdName={household?.name} canManage={household?.permissions.can_manage}>
        {selected && (
          <div className="topbar__month">
            <button
              className="icon-button topbar__month-arrow"
              aria-label={t('month.previous')}
              onClick={() => {
                const p = shiftMonth(selected.year, selected.month, -1);
                goToMonth(p.year, p.month);
              }}
            >
              ‹
            </button>
            <button className="topbar__month-label" onClick={() => setPickerOpen(true)} title={t('month.change')}>
              {monthLabel(selected.year, selected.month, 'short')}
            </button>
            <button
              className="icon-button topbar__month-arrow"
              aria-label={t('month.next')}
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
          {!household && <div className="state-message">{t('common.loading')}</div>}
          {error && <div className="card state-message form-error">{error}</div>}

          {missingMonth && selected && (
            <div className="card state-message">
              {t('month.notCreated', { month: monthLabel(selected.year, selected.month) })}
              {household?.permissions.can_manage ? (
                <div style={{ marginTop: 16 }}>
                  <button className="button button--primary" onClick={handleCreateMonth}>
                    {t('month.create', { month: monthLabel(selected.year, selected.month) })}
                  </button>
                </div>
              ) : (
                <div className="state-message__sub">{t('month.managerCanCreate')}</div>
              )}
              {!isCurrentMonth && (
                <div style={{ marginTop: 12 }}>
                  <button className="button button--ghost" onClick={() => current && goToMonth(current.year, current.month)}>
                    {t('month.goToCurrent')}
                  </button>
                </div>
              )}
            </div>
          )}

          {summary && household && (
            <>
              {summary.month.status === 'closed' && (
                <div className="banner banner--warning">
                  {t('month.closedBanner', { month: monthLabel(summary.month.year, summary.month.month) })}
                </div>
              )}
              {showingOpenLastMonth && current && (
                <p className="month-warning" role="status">
                  <span aria-hidden>⚠</span>
                  <span>
                    {t('month.showingLast', { month: monthLabel(summary.month.year, summary.month.month) })}{' '}
                    <button className="link-button" onClick={() => goToMonth(current.year, current.month)}>
                      {t('month.goTo', { month: monthLabel(current.year, current.month) })}
                    </button>
                  </span>
                </p>
              )}
              {summary.month.status === 'open' && summary.month.auto_close_on && (
                <p className="muted small">
                  {t('month.autoCloses', { date: longDate(summary.month.auto_close_on) })}
                </p>
              )}

              {summary.restricted && (
                <p className="muted small">{t('dashboard.restrictedNote')}</p>
              )}

              <SplitCard summary={summary} onPersonClick={setContactId} onPayClick={setPaying} />

              {!summary.restricted && (
                <section className="card" aria-labelledby="categories-title">
                  <div className="card__header">
                    <h2 className="card__title" id="categories-title">
                      {t('dashboard.byCategory')}
                    </h2>
                    <span className="card__subtitle num">{formatMoney(summary.total, summary.currency)}</span>
                  </div>
                  <CategoryChart totals={summary.category_totals} total={summary.total} currency={summary.currency} />
                </section>
              )}

              <section className="card" aria-labelledby="costs-title">
                <div className="card__header">
                  <h2 className="card__title" id="costs-title">
                    {summary.restricted ? t('dashboard.myCosts') : t('dashboard.costs')}
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
                    + {t('dashboard.addCost')}
                  </Link>
                )}
              </div>
            </>
          )}
        </div>
      </main>

      {confirmClose && summary && householdId && (
        <ConfirmModal
          title={t('month.closeConfirmTitle', { month: monthLabel(summary.month.year, summary.month.month) })}
          confirmLabel={t('monthMenu.close')}
          onClose={() => setConfirmClose(false)}
          onConfirm={async () => {
            try {
              await closeMonth(householdId, summary.month.year, summary.month.month);
              showMessage('success', t('month.closedToast', { month: monthLabel(summary.month.year, summary.month.month) }));
              load();
            } catch (e) {
              showMessage('error', (e as Error).message);
              throw e;
            }
          }}
        >
          {t('month.closeConfirmBody')}
        </ConfirmModal>
      )}
      {deleting && householdId && summary && (
        <ConfirmModal
          title={t('cost.deleteConfirm')}
          confirmLabel={t('common.delete')}
          danger
          onClose={() => setDeleting(null)}
          onConfirm={async () => {
            try {
              await deleteCost(householdId, deleting.id);
              showMessage('success', t('cost.deletedNamed', { name: deleting.description }));
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
          receiver={memberAsReceiver(householdId, summary.members.find((m) => m.id === paying.to_member_id)!)}
          subtitle={t('pay.subtitle', {
            from: summary.members.find((m) => m.id === paying.from_member_id)?.display_name || '',
            to: summary.members.find((m) => m.id === paying.to_member_id)?.display_name || '',
          })}
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
