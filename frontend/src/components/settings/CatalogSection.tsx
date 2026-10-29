import { FormEvent, useCallback, useEffect, useState } from 'react';
import {
  createCategory,
  createPreset,
  deleteCategory,
  deletePreset,
  listCategories,
  listPresets,
  updateCategory,
  updatePreset,
} from '../../api/households';
import type { Category, Preset } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
import { formatMoney, parseAmount } from '../../utils/format';

export function CategoriesSection({ householdId }: { householdId: string }) {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [name, setName] = useState('');
  const showMessage = useMessage();

  const load = useCallback(() => {
    listCategories(householdId, true)
      .then(setCategories)
      .catch((e: Error) => showMessage('error', e.message));
  }, [householdId, showMessage]);
  useEffect(load, [load]);

  const run = async (action: () => Promise<unknown>, success?: string) => {
    try {
      await action();
      if (success) showMessage('success', success);
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  const add = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    run(() => createCategory(householdId, { name: name.trim() }), `Category ${name.trim()} added`).then(() => setName(''));
  };

  const remove = async (c: Category) => {
    if (!window.confirm(`Delete category ${c.name}? If costs use it, it is archived instead.`)) return;
    try {
      const result = await deleteCategory(householdId, c.id);
      showMessage('success', result.deleted ? 'Category deleted' : 'Category is in use, so it was archived');
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  return (
    <section className="card">
      <h2 className="card__title" style={{ marginBottom: 6 }}>
        Categories
      </h2>
      <p className="muted small" style={{ marginBottom: 8 }}>
        Used to group costs and in the monthly chart. Archived categories can't be picked for new costs.
      </p>
      {!categories && <p className="muted">Loading...</p>}
      {categories?.length === 0 && <p className="muted">No categories yet.</p>}
      <div className="list">
        {categories?.map((c) => (
          <div key={c.id} className={`list-item ${c.is_archived ? 'list-item--disabled' : ''}`}>
            <input
              type="color"
              className="form-input"
              defaultValue={c.color || '#6b6b6b'}
              onBlur={(e) => e.target.value !== c.color && run(() => updateCategory(householdId, c.id, { color: e.target.value }))}
              aria-label={`Color of ${c.name}`}
            />
            <input
              className="form-input grow"
              defaultValue={c.name}
              onBlur={(e) => {
                const value = e.target.value.trim();
                if (value && value !== c.name) run(() => updateCategory(householdId, c.id, { name: value }), 'Renamed');
              }}
              aria-label="Category name"
            />
            <button
              className="button button--secondary button--small"
              onClick={() => run(() => updateCategory(householdId, c.id, { is_archived: !c.is_archived }))}
            >
              {c.is_archived ? 'Restore' : 'Archive'}
            </button>
            <button className="button button--danger button--small" onClick={() => remove(c)}>
              Delete
            </button>
          </div>
        ))}
      </div>
      <form className="row" onSubmit={add} style={{ marginTop: 12 }}>
        <input className="form-input grow" placeholder="New category, e.g. Groceries" value={name} onChange={(e) => setName(e.target.value)} />
        <button className="button button--primary">Add</button>
      </form>
    </section>
  );
}

export function PresetsSection({ householdId, currency }: { householdId: string; currency: string }) {
  const [presets, setPresets] = useState<Preset[] | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState({ name: '', category_id: '', amount: '' });
  const showMessage = useMessage();

  const load = useCallback(() => {
    Promise.all([listPresets(householdId), listCategories(householdId)])
      .then(([p, c]) => {
        setPresets(p);
        setCategories(c);
      })
      .catch((e: Error) => showMessage('error', e.message));
  }, [householdId, showMessage]);
  useEffect(load, [load]);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    const amount = parseAmount(form.amount);
    try {
      await createPreset(householdId, {
        name: form.name.trim(),
        category_id: form.category_id || null,
        default_amount: amount > 0 ? amount : null,
      });
      setForm({ name: '', category_id: '', amount: '' });
      load();
    } catch (err) {
      showMessage('error', (err as Error).message);
    }
  };

  const setCategory = async (p: Preset, categoryId: string) => {
    try {
      await updatePreset(householdId, p.id, categoryId ? { category_id: categoryId } : { clear_category: true });
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  const remove = async (p: Preset) => {
    try {
      await deletePreset(householdId, p.id);
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  const categoryOptions = (
    <>
      <option value="">No category</option>
      {categories.map((c) => (
        <option key={c.id} value={c.id}>
          {c.name}
        </option>
      ))}
    </>
  );

  return (
    <section className="card">
      <h2 className="card__title" style={{ marginBottom: 6 }}>
        Cost descriptions
      </h2>
      <p className="muted small" style={{ marginBottom: 8 }}>
        A premade list people can tap when adding a cost. Picking one also fills its category (and amount, if set). People can
        still type any description.
      </p>
      {!presets && <p className="muted">Loading...</p>}
      {presets?.length === 0 && <p className="muted">No descriptions yet.</p>}
      <div className="list">
        {presets?.map((p) => (
          <div key={p.id} className="list-item">
            <div className="list-item__main">
              <div className="list-item__title">{p.name}</div>
              {p.default_amount !== null && <div className="list-item__sub">{formatMoney(p.default_amount, currency)}</div>}
            </div>
            <select
              className="form-select"
              style={{ width: 'auto' }}
              value={p.category_id || ''}
              onChange={(e) => setCategory(p, e.target.value)}
              aria-label={`Category of ${p.name}`}
            >
              {categoryOptions}
            </select>
            <button className="button button--danger button--small" onClick={() => remove(p)}>
              Delete
            </button>
          </div>
        ))}
      </div>
      <form onSubmit={add} style={{ marginTop: 12 }}>
        <div className="form-grid form-grid--3">
          <input className="form-input" placeholder="Description, e.g. Internet" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <select className="form-select" value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
            {categoryOptions}
          </select>
          <input
            className="form-input"
            placeholder="Default amount (optional)"
            inputMode="decimal"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
          />
        </div>
        <button className="button button--primary" style={{ marginTop: 10 }}>
          Add description
        </button>
      </form>
    </section>
  );
}
