import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { listMembers } from '../api/households';
import { createRecurringTask, deleteRecurringTask, listRecurringTasks, listTaskLabels, updateRecurringTask } from '../api/tasks';
import type { AssignMode, FrequencyUnit, Member, RecurringTask, RecurringTaskInput, TaskLabel } from '../api/types';
import { ConfirmModal } from '../components/ConfirmModal';
import { Modal } from '../components/Modal';
import { PersonChips } from '../components/PersonChips';
import { LabelChips, TaskSettingsFields, TaskSettingsValue, taskSettingsOf } from '../components/TaskSettingsFields';
import { TopBar } from '../components/TopBar';
import { useMessage } from '../contexts/MessageContext';
import { useHousehold } from '../hooks/useHousehold';
import { useI18n } from '../i18n';
import { longDate } from '../utils/format';

const UNITS: FrequencyUnit[] = ['day', 'week', 'month'];
const ASSIGN_MODES: AssignMode[] = ['everyone', 'everyone_guests', 'selected'];

/** Managers and residents: tasks created on a schedule (checked whenever someone opens the household). */
export function RecurringTasksPage() {
  const { householdId } = useParams();
  const { household, error: householdError } = useHousehold(householdId);
  const [items, setItems] = useState<RecurringTask[] | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [labels, setLabels] = useState<TaskLabel[]>([]);
  const [editing, setEditing] = useState<RecurringTask | 'new' | null>(null);
  const [deleting, setDeleting] = useState<RecurringTask | null>(null);
  const [error, setError] = useState('');
  const showMessage = useMessage();
  const { t, tn } = useI18n();
  const allowed = household?.permissions.can_add_task;

  const load = useCallback(() => {
    if (!householdId || !allowed) return;
    Promise.all([listRecurringTasks(householdId), listMembers(householdId), listTaskLabels(householdId)])
      .then(([r, m, l]) => {
        setItems(r);
        setMembers(m);
        setLabels(l);
        setError('');
      })
      .catch((e: Error) => setError(e.message));
  }, [householdId, allowed]);
  useEffect(load, [load]);

  const names = new Map(members.map((m) => [m.id, m.display_name]));
  const labelNames = new Map(labels.map((l) => [l.id, l.name]));
  const assignText = (item: RecurringTask) => {
    if (item.assign_mode === 'everyone') return t('recurring.assign.everyone');
    if (item.assign_mode === 'everyone_guests') return t('recurring.assign.everyoneGuests');
    return item.assignee_ids.map((id) => names.get(id) || '?').join(', ') || t('task.unassigned');
  };

  return (
    <>
      <TopBar householdId={householdId} householdName={household?.name} canManage={household?.permissions.can_manage} />
      <main className="page">
        <div className="page__inner page__inner--narrow">
          <Link to={`/h/${householdId}/tasks`} className="back-link">
            ‹ {t('recurring.back')}
          </Link>
          <div>
            <h1 className="page-title">{t('tasks.recurring')}</h1>
            <p className="page-description">{t('recurring.description')}</p>
          </div>

          {householdError && <div className="card state-message">{householdError}</div>}
          {household && !allowed && <div className="card state-message">{t('recurring.notAllowed')}</div>}
          {error && <div className="card state-message form-error">{error}</div>}

          {allowed && (
            <section className="card">
              <div className="card__header">
                <h2 className="card__title">{t('tasks.recurring')}</h2>
                <button className="button button--primary button--small" onClick={() => setEditing('new')}>
                  + {t('recurring.add')}
                </button>
              </div>
              {!items && !error && <p className="muted">{t('common.loading')}</p>}
              {items?.length === 0 && <p className="muted">{t('recurring.empty')}</p>}
              <div className="list">
                {items?.map((item) => (
                  <div key={item.id} className={`list-item ${item.is_active ? '' : 'list-item--disabled'}`}>
                    <button className="list-item__main list-item__button" onClick={() => setEditing(item)}>
                      <div className="list-item__title">
                        {item.title}
                        {[item.category_id, item.location_id].map(
                          (id) => id && labelNames.has(id) && <span key={id} className="tag task-card__category">{labelNames.get(id)}</span>,
                        )}
                        {!item.is_active && <span className="pill" style={{ marginLeft: 8 }}>{t('recurring.paused')}</span>}
                      </div>
                      <div className="list-item__sub">
                        {tn(`recurring.every.${item.unit as FrequencyUnit}`, item.interval)}
                        {item.due_offset_days > 0 && ` · ${tn('recurring.dueLater', item.due_offset_days)}`}
                        {item.next_date && ` · ${t('recurring.next', { date: longDate(item.next_date) })}`}
                      </div>
                      <div className="list-item__sub">{assignText(item)}</div>
                    </button>
                    <button className="button button--secondary button--small" onClick={() => setEditing(item)}>
                      {t('common.edit')}
                    </button>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </main>

      {editing && householdId && household && (
        <RecurringTaskModal
          householdId={householdId}
          item={editing === 'new' ? null : editing}
          members={members}
          labels={labels}
          today={household.today}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            showMessage('success', t('recurring.saved'));
            load();
          }}
          onDelete={(item) => {
            setEditing(null);
            setDeleting(item);
          }}
        />
      )}
      {deleting && householdId && (
        <ConfirmModal
          title={t('recurring.deleteConfirmTitle')}
          confirmLabel={t('common.delete')}
          danger
          onClose={() => setDeleting(null)}
          onConfirm={async () => {
            try {
              await deleteRecurringTask(householdId, deleting.id);
              showMessage('success', t('recurring.deleted', { name: deleting.title }));
              load();
            } catch (e) {
              showMessage('error', (e as Error).message);
              throw e;
            }
          }}
        >
          {t('recurring.deleteConfirm', { name: deleting.title })}
        </ConfirmModal>
      )}
    </>
  );
}

interface ModalProps {
  householdId: string;
  item: RecurringTask | null;
  members: Member[];
  labels: TaskLabel[];
  today: string;
  onClose: () => void;
  onSaved: () => void;
  onDelete: (item: RecurringTask) => void;
}

function RecurringTaskModal({ householdId, item, members, labels, today, onClose, onSaved, onDelete }: ModalProps) {
  const { t } = useI18n();
  const [title, setTitle] = useState(item?.title || '');
  const [categoryId, setCategoryId] = useState<string | null>(item?.category_id || null);
  const [locationId, setLocationId] = useState<string | null>(item?.location_id || null);
  const [description, setDescription] = useState(item?.description || '');
  const [startDate, setStartDate] = useState(item?.start_date || today);
  const [every, setEvery] = useState(String(item?.interval || 1));
  const [unit, setUnit] = useState<FrequencyUnit>((item?.unit as FrequencyUnit) || 'week');
  const [dueOffset, setDueOffset] = useState(item?.due_offset_days || 0);
  const [dueLater, setDueLater] = useState((item?.due_offset_days || 0) > 0);
  const [assignMode, setAssignMode] = useState<AssignMode>((item?.assign_mode as AssignMode) || 'everyone');
  const [assignees, setAssignees] = useState<string[]>(item?.assignee_ids || []);
  const [settings, setSettings] = useState<TaskSettingsValue>(taskSettingsOf(item));
  const [waitForPrevious, setWaitForPrevious] = useState(item?.wait_for_previous ?? true);
  const [active, setActive] = useState(item?.is_active ?? true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const keep = new Set(item?.assignee_ids || []);
  const selectable = members.filter((m) => m.is_participant && (m.is_active || keep.has(m.id)));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return setError(t('validation.title'));
    if (!startDate) return setError(t('validation.date'));
    const body: RecurringTaskInput = {
      title: title.trim(),
      category_id: categoryId,
      location_id: locationId,
      description: description.trim() || null,
      start_date: startDate,
      interval: Math.min(365, Math.max(1, Number(every) || 1)),
      unit,
      due_offset_days: dueLater ? Math.max(1, dueOffset) : 0,
      assign_mode: assignMode,
      assignee_ids: assignMode === 'selected' ? assignees : [],
      wait_for_previous: waitForPrevious,
      is_active: active,
      ...settings,
    };
    setBusy(true);
    try {
      if (item) await updateRecurringTask(householdId, item.id, body);
      else await createRecurringTask(householdId, body);
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={item ? t('recurring.editTitle') : t('recurring.add')} onClose={onClose}>
      <form onSubmit={submit}>
        <div className="form-field">
          <label className="form-label" htmlFor="rt-title">
            {t('task.titleLabel')}
          </label>
          <input
            id="rt-title"
            className="form-input"
            value={title}
            maxLength={200}
            placeholder={t('recurring.titlePlaceholder')}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus={!item}
          />
        </div>
        <LabelChips label={t('task.category')} labels={labels.filter((l) => l.kind === 'category')} value={categoryId} onChange={setCategoryId} />
        <LabelChips label={t('task.location')} labels={labels.filter((l) => l.kind === 'location')} value={locationId} onChange={setLocationId} />
        <div className="form-field">
          <label className="form-label" htmlFor="rt-description">
            {t('task.descriptionOptional')}
          </label>
          <textarea
            id="rt-description"
            className="form-textarea"
            rows={3}
            maxLength={5000}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="form-grid form-grid--2">
          <div className="form-field">
            <label className="form-label" htmlFor="rt-start">
              {t('recurring.startDate')}
            </label>
            <input id="rt-start" className="form-input" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="rt-interval">
              {t('recurring.repeatEvery')}
            </label>
            <div className="inline-field">
              <input
                id="rt-interval"
                className="form-input inline-field__number"
                type="number"
                inputMode="numeric"
                min={1}
                max={365}
                value={every}
                onChange={(e) => setEvery(e.target.value)}
              />
              <select
                className="form-select"
                value={unit}
                onChange={(e) => setUnit(e.target.value as FrequencyUnit)}
                aria-label={t('recurring.repeatEvery')}
              >
                {UNITS.map((u) => (
                  <option key={u} value={u}>
                    {t(`recurring.unit.${u}`)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <fieldset className="form-field form-fieldset">
          <legend className="form-label">{t('recurring.due')}</legend>
          <label className="checkbox">
            <input type="radio" name="rt-due" checked={!dueLater} onChange={() => setDueLater(false)} />
            {t('recurring.dueOnDate')}
          </label>
          <label className="checkbox">
            <input
              type="radio"
              name="rt-due"
              checked={dueLater}
              onChange={() => {
                setDueLater(true);
                if (dueOffset < 1) setDueOffset(3);
              }}
            />
            {t('recurring.dueAfter')}
          </label>
          {dueLater && (
            <div className="inline-field" style={{ marginLeft: 26 }}>
              <input
                className="form-input inline-field__number"
                type="number"
                inputMode="numeric"
                min={1}
                max={365}
                value={dueOffset}
                onChange={(e) => setDueOffset(Math.min(365, Math.max(1, Number(e.target.value) || 1)))}
                aria-label={t('recurring.dueAfterDays')}
              />
              <span>{t('recurring.dueAfterDays')}</span>
            </div>
          )}
        </fieldset>

        <div className="form-field">
          <span className="form-label">{t('recurring.assign')}</span>
          <div className="chips" role="radiogroup" aria-label={t('recurring.assign')}>
            {ASSIGN_MODES.map((mode) => (
              <button
                type="button"
                key={mode}
                role="radio"
                aria-checked={assignMode === mode}
                className={`chip ${assignMode === mode ? 'chip--selected' : ''}`}
                onClick={() => setAssignMode(mode)}
              >
                {t(`recurring.assign.${mode === 'everyone_guests' ? 'everyoneGuests' : mode}`)}
              </button>
            ))}
          </div>
          {assignMode === 'selected' ? (
            <div style={{ marginTop: 10 }}>
              <PersonChips members={selectable} selected={assignees} onChange={setAssignees} label={t('task.assignees')} />
            </div>
          ) : (
            <span className="form-hint">{t('recurring.assignHint')}</span>
          )}
        </div>

        <TaskSettingsFields value={settings} onChange={setSettings} />

        <div className="form-field">
          <label className="checkbox">
            <input type="checkbox" checked={waitForPrevious} onChange={(e) => setWaitForPrevious(e.target.checked)} />
            {t('recurring.wait')}
          </label>
          <span className="form-hint">{t('recurring.waitHint')}</span>
        </div>
        <div className="form-field">
          <label className="checkbox">
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
            {t('recurring.active')}
          </label>
        </div>

        {error && <p className="form-error">{error}</p>}
        <div className="modal__actions">
          {item && (
            <button type="button" className="button button--ghost task-detail__delete" onClick={() => onDelete(item)}>
              {t('common.delete')}
            </button>
          )}
          <button type="button" className="button button--ghost" onClick={onClose} disabled={busy}>
            {t('common.cancel')}
          </button>
          <button className="button button--primary" disabled={busy}>
            {busy ? t('common.saving') : item ? t('common.save') : t('common.add')}
          </button>
        </div>
      </form>
    </Modal>
  );
}
