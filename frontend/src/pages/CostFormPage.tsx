import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { createCost, deleteCost, getCost, listCategories, listMembers, listPresets, updateCost } from '../api/households';
import type { Category, Cost, Member, Preset } from '../api/types';
import { PersonChips } from '../components/PersonChips';
import { TopBar } from '../components/TopBar';
import { useMessage } from '../contexts/MessageContext';
import { useHousehold } from '../hooks/useHousehold';
import { addDays, formatMoney, monthKey, parseAmount } from '../utils/format';

const isResident = (m: Member) => m.role === 'manager' || m.role === 'resident';

/**
 * Add or edit a cost. Built for phones: amount first (numeric keyboard), tap-to-pick
 * presets, categories and people. The /h/:id/add URL is shareable.
 */
export function CostFormPage() {
  const { householdId, costId } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const showMessage = useMessage();
  const { household, error: householdError } = useHousehold(householdId);
  const isEdit = !!costId;

  const [members, setMembers] = useState<Member[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [existing, setExisting] = useState<Cost | null>(null);
  const [loadError, setLoadError] = useState('');
  const [ready, setReady] = useState(false);

  const [amountText, setAmountText] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [date, setDate] = useState('');
  const [payers, setPayers] = useState<string[]>([]);
  const [coverers, setCoverers] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const amountRef = useRef<HTMLInputElement>(null);

  // Load lists (and the cost when editing), then fill in defaults once
  useEffect(() => {
    if (!householdId || !household) return;
    let cancelled = false;
    Promise.all([
      listMembers(householdId),
      listCategories(householdId, isEdit),
      listPresets(householdId),
      costId ? getCost(householdId, costId) : Promise.resolve(null),
    ])
      .then(([memberList, categoryList, presetList, cost]) => {
        if (cancelled) return;
        setMembers(memberList);
        setCategories(categoryList);
        setPresets(presetList);
        setExisting(cost);
        if (cost) {
          setAmountText(String(cost.amount));
          setDescription(cost.description);
          setCategoryId(cost.category_id);
          setDate(cost.date);
          setPayers(cost.payer_ids);
          setCoverers(cost.coverer_ids);
        } else {
          const requested = params.get('date');
          setDate(requested && /^\d{4}-\d{2}-\d{2}$/.test(requested) ? requested : household.today);
          const me = memberList.find((m) => m.id === household.my_member_id && m.is_participant);
          setPayers(me ? [me.id] : []);
          setCoverers(memberList.filter((m) => m.is_active && isResident(m)).map((m) => m.id));
        }
        setReady(true);
      })
      .catch((e: Error) => setLoadError(e.message));
    return () => {
      cancelled = true;
    };
  }, [householdId, costId, household?.id]);

  useEffect(() => {
    if (ready && !isEdit) amountRef.current?.focus();
  }, [ready, isEdit]);

  // People who can be picked: active participants, plus anyone already on the cost
  const selectable = useMemo(() => {
    const keep = new Set([...(existing?.payer_ids || []), ...(existing?.coverer_ids || [])]);
    return members.filter((m) => m.is_participant && (m.is_active || keep.has(m.id)));
  }, [members, existing]);

  const visibleCategories = categories.filter((c) => !c.is_archived || c.id === existing?.category_id);
  // Presets still worth suggesting for what was typed (all of them when the description is empty)
  const matchingPresetIds = useMemo(() => {
    const text = description.trim().toLowerCase();
    const list = text ? presets.filter((p) => p.name.toLowerCase().includes(text) && p.name.toLowerCase() !== text) : presets;
    return new Set(list.map((p) => p.id));
  }, [presets, description]);

  const amount = parseAmount(amountText);
  const currency = household?.currency || 'USD';
  const share = coverers.length > 0 && amount > 0 ? amount / coverers.length : null;

  const applyPreset = (preset: Preset) => {
    setDescription(preset.name);
    if (preset.category_id && categories.some((c) => c.id === preset.category_id && !c.is_archived)) {
      setCategoryId(preset.category_id);
    }
    if (preset.default_amount && !(amount > 0)) setAmountText(String(preset.default_amount));
  };

  const validate = (): string => {
    if (!(amount > 0)) return 'Enter an amount greater than zero';
    if (Math.round(amount * 100) / 100 !== amount) return 'Use at most 2 decimals';
    if (!description.trim()) return 'Enter a description';
    if (!date) return 'Pick a date';
    if (payers.length === 0) return 'Pick who paid';
    if (coverers.length === 0) return 'Pick who covers it';
    return '';
  };

  const save = async (addAnother: boolean) => {
    const problem = validate();
    setFormError(problem);
    if (problem || !householdId) return;
    setSaving(true);
    const body = {
      description: description.trim(),
      category_id: categoryId,
      amount,
      date,
      payer_ids: payers,
      coverer_ids: coverers,
    };
    try {
      if (isEdit && costId) {
        await updateCost(householdId, costId, body);
        showMessage('success', 'Cost updated');
      } else {
        await createCost(householdId, body);
        showMessage('success', `Added ${description.trim()} · ${formatMoney(amount, currency)}`);
      }
      if (addAnother) {
        setAmountText('');
        setDescription('');
        setCategoryId(null);
        amountRef.current?.focus();
        window.scrollTo({ top: 0 });
      } else {
        navigate(backUrl());
      }
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!householdId || !costId || !window.confirm('Delete this cost?')) return;
    try {
      await deleteCost(householdId, costId);
      showMessage('success', 'Cost deleted');
      navigate(backUrl());
    } catch (e) {
      setFormError((e as Error).message);
    }
  };

  const backUrl = () => {
    if (!date || !household) return `/h/${householdId}`;
    const sameAsToday = date.slice(0, 7) === household.today.slice(0, 7);
    return sameAsToday ? `/h/${householdId}` : `/h/${householdId}?m=${monthKey(Number(date.slice(0, 4)), Number(date.slice(5, 7)))}`;
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    save(false);
  };

  const shell = (content: ReactNode) => (
    <>
      <TopBar householdId={householdId} householdName={household?.name} canManage={household?.permissions.can_manage} />
      <main className="page">
        <div className="page__inner page__inner--narrow">{content}</div>
      </main>
    </>
  );

  if (householdError || loadError) return shell(<div className="card state-message">{householdError || loadError}</div>);
  if (!household || !ready) return shell(<div className="state-message">Loading...</div>);
  if (!household.permissions.can_add_cost) {
    return shell(
      <div className="card state-message">
        Viewers can't add costs. Ask a manager if you need to.
        <div style={{ marginTop: 16 }}>
          <Link to={`/h/${householdId}`} className="button button--secondary">
            Back to monthly costs
          </Link>
        </div>
      </div>,
    );
  }
  if (isEdit && existing && !existing.can_edit) {
    return shell(<div className="card state-message">This cost can't be edited (closed month, or added by someone else).</div>);
  }

  return shell(
    <>
      <div className="row row--between">
        <h1 className="page-title">{isEdit ? 'Edit cost' : 'Add cost'}</h1>
        <Link to={backUrl()} className="button button--ghost">
          Cancel
        </Link>
      </div>

      <form id="cost-form" onSubmit={onSubmit} noValidate>
        <section className="card">
          <div className="form-field">
            <label className="form-label" htmlFor="amount">
              Amount ({currency})
            </label>
            <input
              id="amount"
              ref={amountRef}
              className="form-input form-input--amount"
              inputMode="decimal"
              placeholder="0.00"
              value={amountText}
              onChange={(e) => setAmountText(e.target.value)}
              autoComplete="off"
            />
          </div>

          <div className="form-field">
            <label className="form-label" htmlFor="description">
              Description
            </label>
            <input
              id="description"
              className="form-input"
              placeholder="e.g. Groceries"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={200}
              autoComplete="off"
            />
            {presets.length > 0 && (
              // Non-matching presets are hidden but keep their space, so the card doesn't jump while typing
              <div className="chips" style={{ marginTop: 6 }}>
                {presets.map((p) => {
                  const shown = matchingPresetIds.has(p.id);
                  return (
                    <button
                      type="button"
                      key={p.id}
                      className={`chip chip--small ${shown ? '' : 'chip--hidden'}`}
                      onClick={shown ? () => applyPreset(p) : undefined}
                      tabIndex={shown ? undefined : -1}
                      aria-hidden={shown ? undefined : true}
                    >
                      {p.name}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {visibleCategories.length > 0 && (
            <div className="form-field">
              <span className="form-label">Category</span>
              <div className="chips" role="group" aria-label="Category">
                {visibleCategories.map((c) => (
                  <button
                    type="button"
                    key={c.id}
                    className={`chip ${categoryId === c.id ? 'chip--selected' : ''}`}
                    onClick={() => setCategoryId(categoryId === c.id ? null : c.id)}
                    aria-pressed={categoryId === c.id}
                  >
                    <span className="chip__dot" style={{ background: c.color || '#6b6b6b' }} />
                    {c.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="form-field" style={{ marginBottom: 0 }}>
            <label className="form-label" htmlFor="date">
              Date
            </label>
            <div className="row">
              <input id="date" type="date" className="form-input grow" value={date} onChange={(e) => setDate(e.target.value)} style={{ maxWidth: 200 }} />
              <button
                type="button"
                className={`chip chip--small ${date === household.today ? 'chip--selected' : ''}`}
                onClick={() => setDate(household.today)}
              >
                Today
              </button>
              <button
                type="button"
                className={`chip chip--small ${date === addDays(household.today, -1) ? 'chip--selected' : ''}`}
                onClick={() => setDate(addDays(household.today, -1))}
              >
                Yesterday
              </button>
            </div>
          </div>
        </section>

        <section className="card" style={{ marginTop: 16 }}>
          <div className="form-field" style={{ marginBottom: 0 }}>
            <span className="form-label">Who paid</span>
            <PersonChips members={selectable} selected={payers} onChange={setPayers} label="Who paid" />
            {payers.length > 1 && <span className="form-hint">Each paid an equal part.</span>}
          </div>
        </section>

        <section className="card" style={{ marginTop: 16 }}>
          <div className="form-field" style={{ marginBottom: 0 }}>
            <span className="form-label">Who covers</span>
            <PersonChips members={selectable} selected={coverers} onChange={setCoverers} label="Who covers" shortcuts />
            {share !== null && (
              <span className="form-hint" style={{ marginTop: 6 }}>
                {coverers.length === 1 ? 'Covers' : `${coverers.length} people, each covers`}{' '}
                <strong className="num">{formatMoney(share, currency)}</strong>
              </span>
            )}
          </div>
        </section>

        {formError && (
          <p className="form-error" role="alert" style={{ marginTop: 12 }}>
            {formError}
          </p>
        )}

        {/* Right after the last card: two buttons, half the card width each */}
        <div className="form-actions-split">
          {isEdit ? (
            <Link to={backUrl()} className="button button--secondary button--large">
              Cancel
            </Link>
          ) : (
            <button type="button" className="button button--secondary button--large" onClick={() => save(true)} disabled={saving}>
              Save & add another
            </button>
          )}
          <button type="submit" className="button button--primary button--large" disabled={saving}>
            {saving ? 'Saving...' : isEdit ? 'Save changes' : 'Save cost'}
          </button>
        </div>

        {isEdit && (
          <div style={{ marginTop: 24, textAlign: 'center' }}>
            <button type="button" className="button button--danger" onClick={remove}>
              Delete cost
            </button>
          </div>
        )}
      </form>
    </>,
  );
}
