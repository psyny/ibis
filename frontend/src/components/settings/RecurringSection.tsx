import { FormEvent, useCallback, useEffect, useState } from 'react';
import { createRecurring, deleteRecurring, listCategories, listMembers, listRecurring, updateRecurring } from '../../api/households';
import type { Category, Member, RecurringCost } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
import { useI18n } from '../../i18n';
import { formatMoney, parseAmount } from '../../utils/format';
import { PersonChips } from '../PersonChips';

interface Props {
  householdId: string;
  currency: string;
}

/** Fixed costs: copied into every new month when it is created. */
export function RecurringSection({ householdId, currency }: Props) {
  const [items, setItems] = useState<RecurringCost[] | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [editing, setEditing] = useState<RecurringCost | 'new' | null>(null);
  const showMessage = useMessage();
  const { t } = useI18n();

  const load = useCallback(() => {
    Promise.all([listRecurring(householdId), listMembers(householdId), listCategories(householdId, true)])
      .then(([r, m, c]) => {
        setItems(r);
        setMembers(m);
        setCategories(c);
      })
      .catch((e: Error) => showMessage('error', e.message));
  }, [householdId, showMessage]);
  useEffect(load, [load]);

  const names = new Map(members.map((m) => [m.id, m.display_name]));
  const people = (ids: string[]) => ids.map((id) => names.get(id) || '?').join(', ');

  const remove = async (item: RecurringCost) => {
    if (!window.confirm(t('fixed.removeConfirm', { name: item.description }))) return;
    try {
      await deleteRecurring(householdId, item.id);
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  return (
    <section className="card">
      <div className="card__header">
        <h2 className="card__title">{t('settings.tab.fixedCosts')}</h2>
        {editing === null && (
          <button className="button button--primary button--small" onClick={() => setEditing('new')}>
            {t('fixed.add')}
          </button>
        )}
      </div>
      <p className="muted small" style={{ marginBottom: 8 }}>
        {t('fixed.hint')}
      </p>

      {editing !== null && (
        <RecurringForm
          householdId={householdId}
          item={editing === 'new' ? null : editing}
          members={members}
          categories={categories}
          onDone={() => {
            setEditing(null);
            load();
          }}
        />
      )}

      {!items && <p className="muted">{t('common.loading')}</p>}
      {items?.length === 0 && editing === null && <p className="muted">{t('fixed.empty')}</p>}
      <div className="list">
        {items?.map((item) => (
          <div key={item.id} className={`list-item ${item.is_active ? '' : 'list-item--disabled'}`}>
            <div className="list-item__main">
              <div className="list-item__title">
                {item.description} · <span className="num">{formatMoney(item.amount, currency)}</span>
                {!item.is_active && <span className="pill" style={{ marginLeft: 8 }}>{t('fixed.paused')}</span>}
              </div>
              <div className="list-item__sub">
                {t('fixed.day', { day: item.day_of_month })}
                {item.category_name && ` · ${item.category_name}`} · {t('fixed.paidBy', { names: people(item.payer_ids) })} ·{' '}
                {t('fixed.coveredBy', { names: people(item.coverer_ids) })}
              </div>
            </div>
            <button className="button button--secondary button--small" onClick={() => setEditing(item)}>
              {t('common.edit')}
            </button>
            <button className="button button--danger button--small" onClick={() => remove(item)}>
              {t('common.remove')}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

interface FormProps {
  householdId: string;
  item: RecurringCost | null;
  members: Member[];
  categories: Category[];
  onDone: () => void;
}

function RecurringForm({ householdId, item, members, categories, onDone }: FormProps) {
  const residents = members.filter((m) => m.is_active && (m.role === 'manager' || m.role === 'resident'));
  const [description, setDescription] = useState(item?.description || '');
  const [amount, setAmount] = useState(item ? String(item.amount) : '');
  const [day, setDay] = useState(String(item?.day_of_month || 1));
  const [categoryId, setCategoryId] = useState(item?.category_id || '');
  const [payers, setPayers] = useState<string[]>(item?.payer_ids || []);
  const [coverers, setCoverers] = useState<string[]>(item?.coverer_ids || residents.map((m) => m.id));
  const [active, setActive] = useState(item?.is_active ?? true);
  const [error, setError] = useState('');
  const { t } = useI18n();

  const keep = new Set([...(item?.payer_ids || []), ...(item?.coverer_ids || [])]);
  const selectable = members.filter((m) => m.is_participant && (m.is_active || keep.has(m.id)));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const value = parseAmount(amount);
    if (!description.trim()) return setError(t('validation.description'));
    if (!(value > 0)) return setError(t('validation.amountPositive'));
    if (!payers.length || !coverers.length) return setError(t('validation.payersAndCoverers'));
    const body = {
      description: description.trim(),
      amount: value,
      day_of_month: Math.min(31, Math.max(1, Number(day) || 1)),
      category_id: categoryId || null,
      payer_ids: payers,
      coverer_ids: coverers,
      is_active: active,
    };
    try {
      if (item) await updateRecurring(householdId, item.id, body);
      else await createRecurring(householdId, body);
      onDone();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <form onSubmit={submit} className="card" style={{ marginBottom: 12, background: 'rgba(255,255,255,0.03)' }}>
      <div className="form-grid form-grid--3">
        <div className="form-field">
          <label className="form-label" htmlFor="r-desc">
            {t('cost.description')}
          </label>
          <input id="r-desc" className="form-input" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="r-amount">
            {t('fixed.amount')}
          </label>
          <input id="r-amount" className="form-input" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="r-day">
            {t('fixed.dayOfMonth')}
          </label>
          <input id="r-day" className="form-input" type="number" min={1} max={31} value={day} onChange={(e) => setDay(e.target.value)} />
        </div>
      </div>
      <div className="form-field">
        <label className="form-label" htmlFor="r-cat">
          {t('cost.category')}
        </label>
        <select id="r-cat" className="form-select" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">{t('categories.none')}</option>
          {categories
            .filter((c) => !c.is_archived || c.id === item?.category_id)
            .map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
        </select>
      </div>
      <div className="form-field">
        <span className="form-label">{t('fixed.whoPays')}</span>
        <PersonChips members={selectable} selected={payers} onChange={setPayers} label={t('fixed.whoPays')} />
      </div>
      <div className="form-field">
        <span className="form-label">{t('cost.whoCovers')}</span>
        <PersonChips members={selectable} selected={coverers} onChange={setCoverers} label={t('cost.whoCovers')} shortcuts />
      </div>
      <label className="checkbox" style={{ marginBottom: 12 }}>
        <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
        {t('fixed.active')}
      </label>
      {error && <p className="form-error" style={{ marginBottom: 12 }}>{error}</p>}
      <div className="row">
        <button className="button button--primary">{item ? t('common.save') : t('common.add')}</button>
        <button type="button" className="button button--ghost" onClick={onDone}>
          {t('common.cancel')}
        </button>
      </div>
    </form>
  );
}
