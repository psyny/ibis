import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { listMembers } from '../api/households';
import { completeTask, deleteTask, getTask, listTaskLabels, listTasks } from '../api/tasks';
import type { Member, Task, TaskLabel } from '../api/types';
import { ConfirmModal } from '../components/ConfirmModal';
import { ActionsMenu } from '../components/ActionsMenu';
import { TaskActionsIcon, TrashIcon } from '../components/icons';
import { TaskModal } from '../components/TaskModal';
import { TopBar } from '../components/TopBar';
import { useMessage } from '../contexts/MessageContext';
import { useHousehold } from '../hooks/useHousehold';
import { useI18n } from '../i18n';
import { notificationsChanged } from '../utils/notifications';
import { dueText, taskTitle } from '../utils/tasks';

/** Household tasks: pending ones by due date (red overdue, yellow expiring), with filters. ?task=<id> opens one. */
export function TasksPage() {
  const { householdId } = useParams();
  const [params, setParams] = useSearchParams();
  const { household, error: householdError } = useHousehold(householdId);
  const [members, setMembers] = useState<Member[]>([]);
  const [labels, setLabels] = useState<TaskLabel[]>([]);
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [error, setError] = useState('');
  const [showCompleted, setShowCompleted] = useState(false);
  // undefined = the default: tasks assigned to me (everyone's when I'm not a member, e.g. an admin)
  const [assigneeChoice, setAssigneeChoice] = useState<string | null | undefined>(undefined);
  const [thisMonth, setThisMonth] = useState(false);
  const [categoryId, setCategoryId] = useState<string | null>(null); // null = all
  const [locationId, setLocationId] = useState<string | null>(null);
  const [opened, setOpened] = useState<Task | null>(null);
  const [adding, setAdding] = useState(false);
  const [deleting, setDeleting] = useState<Task | null>(null);
  const showMessage = useMessage();
  const i18n = useI18n();
  const { t } = i18n;

  const today = household?.today;
  const isGuest = household?.my_role === 'guest';
  const myId = household?.my_member_id || null;
  const assigneeId = assigneeChoice === undefined ? (isGuest ? null : myId) : assigneeChoice;
  const setAssigneeId = (id: string | null) => setAssigneeChoice(id);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    if (!householdId || !today) return;
    try {
      const list = await listTasks(householdId, {
        includeCompleted: showCompleted,
        assigneeId,
        dueMonth: thisMonth ? today.slice(0, 7) : null,
        categoryId,
        locationId,
      });
      setTasks(list);
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }, [householdId, today, showCompleted, assigneeId, thisMonth, categoryId, locationId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!householdId) return;
    listMembers(householdId).then(setMembers).catch(() => undefined);
    listTaskLabels(householdId).then(setLabels).catch(() => undefined);
  }, [householdId]);

  // ?task=<id> (from a notification or a tap on a card): open that task, even if it's not in the list
  const openId = params.get('task');
  useEffect(() => {
    if (!householdId || !openId) {
      setOpened(null);
      return;
    }
    const inList = tasks?.find((task) => task.id === openId);
    if (inList) {
      setOpened(inList);
      return;
    }
    let cancelled = false;
    getTask(householdId, openId)
      .then((task) => !cancelled && setOpened(task))
      .catch(() => {
        if (cancelled) return;
        showMessage('info', t('task.notFound'));
        closeTask();
      });
    return () => {
      cancelled = true;
    };
  }, [householdId, openId]);

  const openTask = (task: Task) => {
    setOpened(task);
    setParams({ task: task.id });
  };
  const closeTask = () => {
    setOpened(null);
    const next = new URLSearchParams(params);
    next.delete('task');
    setParams(next, { replace: true });
  };

  const toggle = async (task: Task) => {
    if (!householdId) return;
    const done = task.status !== 'completed';
    try {
      await completeTask(householdId, task.id, done);
      notificationsChanged();
      showMessage('success', t(done ? 'task.completedToast' : 'task.reopenedToast', { name: taskTitle(task, t) }));
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  const names = new Map(members.map((m) => [m.id, m.display_name]));
  const assignable = members.filter((m) => m.is_participant && m.is_active);
  const filtered = showCompleted || assigneeId !== null || thisMonth || !!categoryId || !!locationId;
  const onlyMine = !!myId && assigneeId === myId && !showCompleted && !thisMonth && !categoryId && !locationId;
  const labelFilter = (kind: TaskLabel['kind'], value: string | null, set: (id: string | null) => void) => {
    const options = labels.filter((l) => l.kind === kind);
    if (options.length === 0) return null;
    const name = kind === 'category' ? t('task.category') : t('task.location');
    return (
      <select
        className={`form-select task-filters__select ${value ? 'task-filters__select--on' : ''}`}
        value={value || ''}
        onChange={(e) => set(e.target.value || null)}
        aria-label={name}
      >
        <option value="">
          {name}: {t('tasks.all')}
        </option>
        {options.map((l) => (
          <option key={l.id} value={l.id}>
            {name}: {l.name}
          </option>
        ))}
      </select>
    );
  };

  return (
    <>
      <TopBar householdId={householdId} householdName={household?.name} canManage={household?.permissions.can_manage}>
        {household?.permissions.can_add_task && (
          <ActionsMenu icon={<TaskActionsIcon size={22} />} label={t('tasks.actions')} title={t('tasks.actions')}>
            {(close) => (
              <>
                <div className="menu__label">{t('tasks.title')}</div>
                <button
                  className="menu__item"
                  onClick={() => {
                    close();
                    setAdding(true);
                  }}
                >
                  {t('tasks.add')}
                </button>
                <button
                  className="menu__item"
                  onClick={() => {
                    close();
                    navigate(`/h/${householdId}/tasks/recurring`);
                  }}
                >
                  {t('tasks.recurring')}
                  <span className="menu__hint">{t('tasks.recurringHint')}</span>
                </button>
              </>
            )}
          </ActionsMenu>
        )}
      </TopBar>
      <main className="page">
        <div className="page__inner page__inner--narrow">
          <div>
            <h1 className="page-title">{t('tasks.title')}</h1>
            <p className="page-description">{isGuest ? t('tasks.descriptionGuest') : t('tasks.description')}</p>
          </div>

          {householdError && <div className="card state-message">{householdError}</div>}

          <div className="task-filters" role="group" aria-label={t('tasks.filters')}>
            <button
              className={`chip chip--small ${showCompleted ? 'chip--selected' : ''}`}
              aria-pressed={showCompleted}
              onClick={() => setShowCompleted((v) => !v)}
            >
              {t('tasks.showCompleted')}
            </button>
            {!isGuest && myId && (
              <button
                className={`chip chip--small ${assigneeId === myId ? 'chip--selected' : ''}`}
                aria-pressed={assigneeId === myId}
                onClick={() => setAssigneeId(assigneeId === myId ? null : myId)}
              >
                {t('tasks.assignedToMe')}
              </button>
            )}
            <button
              className={`chip chip--small ${thisMonth ? 'chip--selected' : ''}`}
              aria-pressed={thisMonth}
              onClick={() => setThisMonth((v) => !v)}
            >
              {t('tasks.thisMonth')}
            </button>
            {!isGuest && (
              <select
                className={`form-select task-filters__select ${assigneeId ? 'task-filters__select--on' : ''}`}
                value={assigneeId || ''}
                onChange={(e) => setAssigneeId(e.target.value || null)}
                aria-label={t('tasks.assignedTo')}
              >
                <option value="">
                  {t('tasks.assignedTo')}: {t('tasks.anyone')}
                </option>
                {assignable.map((m) => (
                  <option key={m.id} value={m.id}>
                    {t('tasks.assignedTo')}: {m.display_name}
                  </option>
                ))}
              </select>
            )}
            {labelFilter('category', categoryId, setCategoryId)}
            {labelFilter('location', locationId, setLocationId)}
          </div>

          {error && <div className="card state-message form-error">{error}</div>}
          {!error && tasks === null && <div className="state-message">{t('common.loading')}</div>}
          {tasks?.length === 0 && (
            <div className="card state-message">
              {onlyMine ? t('tasks.emptyMine') : filtered ? t('tasks.emptyFiltered') : t('tasks.empty')}
              {onlyMine && <div className="state-message__sub">{t('tasks.emptyMineHint')}</div>}
            </div>
          )}
          {tasks && tasks.length > 0 && today && (
            <div className="task-list">
              {tasks.map((task) => {
                const done = task.status === 'completed';
                const title = taskTitle(task, t);
                const people = task.assignee_ids.map((id) => names.get(id) || '?').join(', ');
                return (
                  <div key={task.id} className={`task-card task-card--${task.status}`}>
                    {task.can_complete ? (
                      <button
                        className={`task-card__check ${done ? 'task-card__check--done' : ''}`}
                        onClick={() => toggle(task)}
                        aria-label={t(done ? 'task.uncompleteAria' : 'task.completeAria', { name: title })}
                        title={done ? t('task.uncomplete') : t('task.complete')}
                      >
                        {done && '✓'}
                      </button>
                    ) : (
                      <span className="task-card__check task-card__check--placeholder" aria-hidden />
                    )}
                    <button className="task-card__main" onClick={() => openTask(task)}>
                      <span className="task-card__title">
                        {title}
                        {task.category_name && <span className="tag task-card__category">{task.category_name}</span>}
                      </span>
                      <span className="task-card__meta">
                        <span className="task-card__due">{done ? t('task.status.completed') : dueText(task, today, i18n)}</span>
                        {task.location_name && <span> · {task.location_name}</span>}
                        {people && <span> · {people}</span>}
                      </span>
                    </button>
                    {task.can_delete && (
                      <button
                        className="icon-button task-card__delete"
                        onClick={() => setDeleting(task)}
                        aria-label={t('task.deleteAria', { name: title })}
                        title={t('common.delete')}
                      >
                        <TrashIcon size={18} />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {household?.permissions.can_add_task && (
            <div className="page-actions">
              <button className="button button--primary button--large" onClick={() => setAdding(true)}>
                + {t('tasks.add')}
              </button>
            </div>
          )}
        </div>
      </main>

      {(opened || adding) && householdId && today && (
        <TaskModal
          key={opened?.id || 'new'}
          householdId={householdId}
          task={adding ? null : opened}
          members={members}
          labels={labels}
          today={today}
          onClose={() => (adding ? setAdding(false) : closeTask())}
          onChanged={(task) => {
            if (!adding) setOpened(task);
            load();
          }}
          onDelete={(task) => {
            closeTask();
            setDeleting(task);
          }}
        />
      )}
      {deleting && householdId && (
        <ConfirmModal
          title={t('task.deleteConfirm')}
          confirmLabel={t('common.delete')}
          danger
          onClose={() => setDeleting(null)}
          onConfirm={async () => {
            try {
              await deleteTask(householdId, deleting.id);
              notificationsChanged();
              showMessage('success', t('task.deletedToast', { name: taskTitle(deleting, t) }));
              load();
            } catch (e) {
              showMessage('error', (e as Error).message);
              throw e;
            }
          }}
        >
          {taskTitle(deleting, t)}
        </ConfirmModal>
      )}
    </>
  );
}
