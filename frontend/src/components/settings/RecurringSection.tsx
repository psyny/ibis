import { FormEvent, useCallback, useEffect, useState } from 'react';
import { createRecurring, deleteRecurring, listCategories, listMembers, listRecurring, updateRecurring } from '../../api/households';
import type { Category, Member, RecurringCost } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
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
    if (!window.confirm(`Remove ${item.description} from the fixed costs? Months that already have it keep it.`)) return;
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
        <h2 className="card__title">Fixed costs</h2>
        {editing === null && (
          <button className="button button--primary button--small" onClick={() => setEditing('new')}>
            Add fixed cost
          </button>
        )}
      </div>
      <p className="muted small" style={{ marginBottom: 8 }}>
        Fixed costs (rent, internet...) copied into every new month when it is created. To add them to a month that already exists,
        use “Add fixed costs” in the month menu (calendar icon at the top). It never adds duplicates.
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

      {!items && <p className="muted">Loading...</p>}
      {items?.length === 0 && editing === null && <p className="muted">No fixed costs yet.</p>}
      <div className="list">
        {items?.map((item) => (
          <div key={item.id} className={`list-item ${item.is_active ? '' : 'list-item--disabled'}`}>
            <div className="list-item__main">
              <div className="list-item__title">
                {item.description} · <span className="num">{formatMoney(item.amount, currency)}</span>
                {!item.is_active && <span className="pill" style={{ marginLeft: 8 }}>Paused</span>}
              </div>
              <div className="list-item__sub">
                Day {item.day_of_month}
                {item.category_name && ` · ${item.category_name}`} · Paid by {people(item.payer_ids)} · Covered by{' '}
                {people(item.coverer_ids)}
              </div>
            </div>
            <button className="button button--secondary button--small" onClick={() => setEditing(item)}>
              Edit
            </button>
            <button className="button button--danger button--small" onClick={() => remove(item)}>
              Remove
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

  const keep = new Set([...(item?.payer_ids || []), ...(item?.coverer_ids || [])]);
  const selectable = members.filter((m) => m.is_participant && (m.is_active || keep.has(m.id)));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const value = parseAmount(amount);
    if (!description.trim()) return setError('Enter a description');
    if (!(value > 0)) return setError('Enter an amount greater than zero');
    if (!payers.length || !coverers.length) return setError('Pick who pays and who covers');
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
            Description
          </label>
          <input id="r-desc" className="form-input" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="r-amount">
            Amount
          </label>
          <input id="r-amount" className="form-input" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="r-day">
            Day of month
          </label>
          <input id="r-day" className="form-input" type="number" min={1} max={31} value={day} onChange={(e) => setDay(e.target.value)} />
        </div>
      </div>
      <div className="form-field">
        <label className="form-label" htmlFor="r-cat">
          Category
        </label>
        <select id="r-cat" className="form-select" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">No category</option>
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
        <span className="form-label">Who pays</span>
        <PersonChips members={selectable} selected={payers} onChange={setPayers} label="Who pays" />
      </div>
      <div className="form-field">
        <span className="form-label">Who covers</span>
        <PersonChips members={selectable} selected={coverers} onChange={setCoverers} label="Who covers" shortcuts />
      </div>
      <label className="checkbox" style={{ marginBottom: 12 }}>
        <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
        Active (copied into new months)
      </label>
      {error && <p className="form-error" style={{ marginBottom: 12 }}>{error}</p>}
      <div className="row">
        <button className="button button--primary">{item ? 'Save' : 'Add'}</button>
        <button type="button" className="button button--ghost" onClick={onDone}>
          Cancel
        </button>
      </div>
    </form>
  );
}
