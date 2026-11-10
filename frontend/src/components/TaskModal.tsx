import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { completeTask, createTask, updateTask } from '../api/tasks';
import type { Member, Task, TaskInput, TaskLabel } from '../api/types';
import { useMessage } from '../contexts/MessageContext';
import { useI18n } from '../i18n';
import { longDate } from '../utils/format';
import { monthPaymentData, notificationsChanged, paymentLink } from '../utils/notifications';
import { dueText, taskDescription, taskTitle } from '../utils/tasks';
import { Modal } from './Modal';
import { PaymentWays } from './PaymentWays';
import { PersonChips } from './PersonChips';
import { LabelChips, notifySummary, TaskSettingsFields, TaskSettingsValue, taskSettingsOf } from './TaskSettingsFields';

interface Props {
  householdId: string;
  /** null: adding a new task */
  task: Task | null;
  members: Member[];
  /** The household's task categories and locations */
  labels: TaskLabel[];
  today: string;
  onClose: () => void;
  /** After a save or a (un)complete: the updated task */
  onChanged: (task: Task) => void;
  onDelete: (task: Task) => void;
}

/** A task's full details and actions; also the add/edit form. */
export function TaskModal({ householdId, task, members, labels, today, onClose, onChanged, onDelete }: Props) {
  const [editing, setEditing] = useState(task === null);
  const { t } = useI18n();

  if (editing) {
    return (
      <Modal title={task ? t('task.editTitle') : t('task.addTitle')} onClose={onClose}>
        <TaskForm
          householdId={householdId}
          task={task}
          members={members}
          labels={labels}
          onCancel={() => (task ? setEditing(false) : onClose())}
          onSaved={(saved) => {
            setEditing(false);
            onChanged(saved);
            if (!task) onClose();
          }}
        />
      </Modal>
    );
  }
  return (
    <TaskDetails
      householdId={householdId}
      task={task!}
      members={members}
      today={today}
      onClose={onClose}
      onEdit={() => setEditing(true)}
      onChanged={onChanged}
      onDelete={onDelete}
    />
  );
}

interface DetailsProps extends Omit<Props, 'task' | 'labels'> {
  task: Task;
  onEdit: () => void;
}

function TaskDetails({ householdId, task, members, today, onClose, onEdit, onChanged, onDelete }: DetailsProps) {
  const i18n = useI18n();
  const { t, tn } = i18n;
  const showMessage = useMessage();
  const [busy, setBusy] = useState(false);
  const names = new Map(members.map((m) => [m.id, m.display_name]));
  const assignees = task.assignee_ids.map((id) => names.get(id) || '?').join(', ');
  const description = taskDescription(task, t);
  const payment = monthPaymentData(task.kind, task.data);
  const done = task.status === 'completed';
  const notify = notifySummary(task, t);

  const toggle = async () => {
    setBusy(true);
    try {
      const updated = await completeTask(householdId, task.id, !done);
      notificationsChanged(); // completing marks its notes as read
      onChanged(updated);
    } catch (e) {
      showMessage('error', (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={taskTitle(task, t)} onClose={onClose}>
      <div className={`task-status task-status--${task.status}`}>
        {done ? t('task.status.completed') : dueText(task, today, i18n)}
      </div>
      <p className={`task-detail__description${description ? '' : ' muted'}`}>{description || t('task.noDescription')}</p>
      {payment && 'pix_key' in payment && !done && <PaymentWays payment={payment} />}
      <dl className="task-detail__facts">
        <dt>{t('task.category')}</dt>
        <dd>{task.category_name || t('task.noCategory')}</dd>
        <dt>{t('task.location')}</dt>
        <dd>{task.location_name || t('task.noLocation')}</dd>
        <dt>{t('task.dueDate')}</dt>
        <dd>{task.due_date ? longDate(task.due_date) : t('task.noDue')}</dd>
        <dt>{t('task.assignees')}</dt>
        <dd>{assignees || t('task.unassigned')}</dd>
        <dt>{t('task.createdBy')}</dt>
        <dd>
          {task.created_by_name || t('task.createdByApp')} · {longDate(task.created_at.slice(0, 10))}
          {task.recurring_task_id && <div className="muted small">{t('task.fromRecurring')}</div>}
        </dd>
        {task.completed_at && (
          <>
            <dt>{t('task.completedBy')}</dt>
            <dd>
              {task.completed_by_name || '?'} · {longDate(task.completed_at.slice(0, 10))}
            </dd>
          </>
        )}
        <dt>{t('task.warnDays')}</dt>
        <dd>{tn('task.warnDaysValue', task.warn_days)}</dd>
        <dt>{t('task.notifications')}</dt>
        <dd>
          {notify.length ? notify.map((line) => <div key={line}>{line}</div>) : t('task.notifyOff')}
        </dd>
        {task.is_private && (
          <>
            <dt>{t('task.private')}</dt>
            <dd>{t('task.privateHint')}</dd>
          </>
        )}
      </dl>
      {payment && (
        <Link to={paymentLink(householdId, payment)} className="button button--secondary button--block">
          {t('task.openPayment')}
        </Link>
      )}
      <div className="modal__actions">
        {task.can_delete && (
          <button className="button button--ghost task-detail__delete" onClick={() => onDelete(task)}>
            {t('common.delete')}
          </button>
        )}
        {task.can_edit && (
          <button className="button button--secondary" onClick={onEdit}>
            {t('common.edit')}
          </button>
        )}
        {task.can_complete && (
          <button className={`button ${done ? 'button--secondary' : 'button--primary'}`} onClick={toggle} disabled={busy}>
            {done ? t('task.uncomplete') : t('task.complete')}
          </button>
        )}
      </div>
    </Modal>
  );
}

interface FormProps {
  householdId: string;
  task: Task | null;
  members: Member[];
  labels: TaskLabel[];
  onCancel: () => void;
  onSaved: (task: Task) => void;
}

function TaskForm({ householdId, task, members, labels, onCancel, onSaved }: FormProps) {
  const { t } = useI18n();
  const showMessage = useMessage();
  const [title, setTitle] = useState(task?.title || '');
  const [categoryId, setCategoryId] = useState<string | null>(task?.category_id || null);
  const [locationId, setLocationId] = useState<string | null>(task?.location_id || null);
  const [description, setDescription] = useState(task?.description || '');
  const [dueDate, setDueDate] = useState(task?.due_date || '');
  const [assignees, setAssignees] = useState<string[]>(task?.assignee_ids || []);
  const [settings, setSettings] = useState<TaskSettingsValue>(taskSettingsOf(task));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const keep = new Set(task?.assignee_ids || []);
  const selectable = members.filter((m) => m.is_participant && (m.is_active || keep.has(m.id)));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return setError(t('validation.title'));
    const body: TaskInput = {
      title: title.trim(),
      category_id: categoryId,
      location_id: locationId,
      description: description.trim() || null,
      due_date: dueDate || null,
      assignee_ids: assignees,
      ...settings,
    };
    setBusy(true);
    try {
      const saved = task ? await updateTask(householdId, task.id, body) : await createTask(householdId, body);
      showMessage('success', task ? t('task.savedToast') : t('task.addedToast', { name: saved.title }));
      notificationsChanged(); // a due date in the warning window may notify right away
      onSaved(saved);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}>
      <div className="form-field">
        <label className="form-label" htmlFor="task-title">
          {t('task.titleLabel')}
        </label>
        <input
          id="task-title"
          className="form-input"
          value={title}
          maxLength={200}
          placeholder={t('task.titlePlaceholder')}
          onChange={(e) => setTitle(e.target.value)}
          autoFocus={!task}
        />
      </div>
      <LabelChips label={t('task.category')} labels={labels.filter((l) => l.kind === 'category')} value={categoryId} onChange={setCategoryId} />
      <LabelChips label={t('task.location')} labels={labels.filter((l) => l.kind === 'location')} value={locationId} onChange={setLocationId} />
      <div className="form-field">
        <label className="form-label" htmlFor="task-description">
          {t('task.descriptionOptional')}
        </label>
        <textarea
          id="task-description"
          className="form-textarea"
          rows={4}
          maxLength={5000}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <div className="form-field">
        <label className="form-label" htmlFor="task-due">
          {t('task.dueDate')}
        </label>
        <input id="task-due" className="form-input" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        <span className="form-hint">{t('task.dueDateHint')}</span>
      </div>
      <div className="form-field">
        <span className="form-label">{t('task.assignees')}</span>
        <PersonChips members={selectable} selected={assignees} onChange={setAssignees} label={t('task.assignees')} shortcuts />
      </div>
      <TaskSettingsFields value={settings} onChange={setSettings} />
      {error && <p className="form-error">{error}</p>}
      <div className="modal__actions">
        <button type="button" className="button button--ghost" onClick={onCancel} disabled={busy}>
          {t('common.cancel')}
        </button>
        <button className="button button--primary" disabled={busy}>
          {busy ? t('common.saving') : task ? t('common.save') : t('common.add')}
        </button>
      </div>
    </form>
  );
}
