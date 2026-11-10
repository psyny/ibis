import { FormEvent, useCallback, useEffect, useState } from 'react';
import { createTaskLabel, deleteTaskLabel, listTaskLabels, renameTaskLabel } from '../../api/tasks';
import type { TaskLabel } from '../../api/types';
import { useMessage } from '../../contexts/MessageContext';
import { useI18n } from '../../i18n';

/** Managers: the household's task categories or locations (they start with a default list). */
export function TaskLabelsSection({ householdId, kind }: { householdId: string; kind: TaskLabel['kind'] }) {
  const [labels, setLabels] = useState<TaskLabel[] | null>(null);
  const showMessage = useMessage();

  const load = useCallback(() => {
    listTaskLabels(householdId)
      .then(setLabels)
      .catch((e: Error) => showMessage('error', e.message));
  }, [householdId, showMessage]);
  useEffect(load, [load]);

  return <LabelList householdId={householdId} kind={kind} labels={labels} onChanged={load} />;
}

interface ListProps {
  householdId: string;
  kind: TaskLabel['kind'];
  labels: TaskLabel[] | null;
  onChanged: () => void;
}

function LabelList({ householdId, kind, labels, onChanged }: ListProps) {
  const [name, setName] = useState('');
  const showMessage = useMessage();
  const { t } = useI18n();
  const items = labels?.filter((l) => l.kind === kind) || null;
  const isCategory = kind === 'category';

  const run = async (action: () => Promise<unknown>, success: string) => {
    try {
      await action();
      showMessage('success', success);
      onChanged();
      return true;
    } catch (e) {
      showMessage('error', (e as Error).message);
      return false;
    }
  };

  const add = async (e: FormEvent) => {
    e.preventDefault();
    const value = name.trim();
    if (!value) return;
    if (await run(() => createTaskLabel(householdId, { kind, name: value }), t('taskLabels.added', { name: value }))) setName('');
  };

  const remove = (label: TaskLabel) => {
    if (!window.confirm(t('taskLabels.deleteConfirm', { name: label.name }))) return;
    run(() => deleteTaskLabel(householdId, label.id), t('taskLabels.deleted', { name: label.name }));
  };

  return (
    <section className="card">
      <h2 className="card__title" style={{ marginBottom: 6 }}>
        {isCategory ? t('taskLabels.categoriesTitle') : t('taskLabels.locationsTitle')}
      </h2>
      <p className="muted small" style={{ marginBottom: 8 }}>
        {isCategory ? t('taskLabels.categoriesHint') : t('taskLabels.locationsHint')}
      </p>
      {!items && <p className="muted">{t('common.loading')}</p>}
      {items?.length === 0 && <p className="muted">{t('taskLabels.empty')}</p>}
      <div className="list">
        {items?.map((label) => (
          <div key={label.id} className="list-item">
            <input
              className="form-input grow"
              defaultValue={label.name}
              maxLength={100}
              aria-label={t('common.name')}
              onBlur={(e) => {
                const value = e.target.value.trim();
                if (value && value !== label.name) run(() => renameTaskLabel(householdId, label.id, value), t('categories.renamed'));
              }}
            />
            <button className="button button--danger button--small" onClick={() => remove(label)}>
              {t('common.delete')}
            </button>
          </div>
        ))}
      </div>
      <form className="row" onSubmit={add} style={{ marginTop: 12 }}>
        <input
          className="form-input grow"
          maxLength={100}
          placeholder={isCategory ? t('taskLabels.newCategory') : t('taskLabels.newLocation')}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button className="button button--primary">{t('common.add')}</button>
      </form>
    </section>
  );
}
