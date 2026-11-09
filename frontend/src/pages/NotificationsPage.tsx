import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { deleteNotification, listNotifications, restoreNotification } from '../api/notifications';
import type { AppNotification, NotificationBox } from '../api/types';
import { TrashIcon } from '../components/icons';
import { TopBar } from '../components/TopBar';
import { lastHousehold, useAuth } from '../contexts/AuthContext';
import { useMessage } from '../contexts/MessageContext';
import { useOpenNotification } from '../hooks/useNotifications';
import { useI18n } from '../i18n';
import { shortDate } from '../utils/format';
import { notificationText, notificationsChanged, onNotificationsChanged } from '../utils/notifications';

const BOXES: NotificationBox[] = ['inbox', 'deleted'];

/** The user's notification inbox, with a Deleted tab. */
export function NotificationsPage() {
  const { me } = useAuth();
  const { t } = useI18n();
  const showMessage = useMessage();
  const open = useOpenNotification();
  const [params, setParams] = useSearchParams();
  const box = (BOXES as string[]).includes(params.get('box') || '') ? (params.get('box') as NotificationBox) : 'inbox';
  const [items, setItems] = useState<AppNotification[] | null>(null);
  const [error, setError] = useState('');

  const householdId = lastHousehold() || me?.households[0]?.id;
  const current = me?.households.find((h) => h.id === householdId);

  const load = useCallback(async () => {
    try {
      setItems(await listNotifications(box));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }, [box]);

  useEffect(() => {
    setItems(null);
    load();
    return onNotificationsChanged(load);
  }, [load]);

  const run = (action: (id: string) => Promise<unknown>) => async (n: AppNotification) => {
    try {
      await action(n.id);
      notificationsChanged(); // reloads this list and the top bar
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  const empty = box === 'inbox' ? t('notif.empty.inbox') : t('notif.empty.deleted');

  return (
    <>
      <TopBar householdId={householdId} householdName={current?.name} canManage={current?.role === 'manager'} hideNotificationBar />
      <main className="page">
        <div className="page__inner page__inner--narrow">
          <div>
            <h1 className="page-title">{t('notif.title')}</h1>
            <p className="page-description">{t('notif.description')}</p>
          </div>
          <nav className="tabs" aria-label={t('notif.title')}>
            {BOXES.map((id) => (
              <button
                key={id}
                className={`tab ${box === id ? 'tab--active' : ''}`}
                onClick={() => setParams(id === 'inbox' ? {} : { box: id })}
              >
                {t(`notif.tab.${id}`)}
              </button>
            ))}
          </nav>

          {error && <div className="state-message">{error}</div>}
          {!error && items === null && <div className="state-message">{t('common.loading')}</div>}
          {items && items.length === 0 && <div className="state-message">{empty}</div>}
          {items && items.length > 0 && (
            <div className="notif-list">
              {items.map((n) => {
                const text = notificationText(n, t);
                return (
                  <div key={n.id} className={`notif-item${n.viewed_at ? '' : ' notif-item--new'}`}>
                    <button className="notif-item__main" onClick={() => open(n)}>
                      <span className="notif-item__icon" aria-hidden>
                        •
                      </span>
                      <span className="notif-item__text">
                        <span className="notif-item__title">{text.title}</span>
                        <span className="notif-item__body">
                          {shortDate(n.created_at.slice(0, 10))}
                          {text.body ? ` · ${text.body}` : ''}
                        </span>
                      </span>
                    </button>
                    <div className="notif-item__actions">
                      {box === 'deleted' ? (
                        <button className="button button--ghost button--small" onClick={() => run(restoreNotification)(n)}>
                          {t('notif.restore')}
                        </button>
                      ) : (
                        <button
                          className="icon-button"
                          onClick={() => run(deleteNotification)(n)}
                          aria-label={t('notif.delete')}
                          title={t('notif.delete')}
                        >
                          <TrashIcon size={18} />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
