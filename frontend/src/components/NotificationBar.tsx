import { Link } from 'react-router-dom';
import { completeNotification, viewNotification } from '../api/notifications';
import type { AppNotification } from '../api/types';
import { useMessage } from '../contexts/MessageContext';
import { useOpenNotification } from '../hooks/useNotifications';
import { useI18n } from '../i18n';
import { notificationText, notificationsChanged } from '../utils/notifications';

interface Props {
  items: AppNotification[];
}

/** Strip under the top bar: latest notes not viewed yet and tasks not done yet (up to 5). */
export function NotificationBar({ items }: Props) {
  const { t } = useI18n();
  const open = useOpenNotification();
  const showMessage = useMessage();

  if (items.length === 0) return null;

  const act = async (n: AppNotification) => {
    try {
      // Tasks are marked done; notes are just dismissed (marked viewed)
      await (n.type === 'task' ? completeNotification(n.id) : viewNotification(n.id));
      notificationsChanged();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  return (
    <section className="notif-bar" aria-label={t('notif.barLabel')}>
      <div className="notif-bar__inner">
        {items.map((n) => {
          const text = notificationText(n, t);
          return (
            <div key={n.id} className={`notif-item notif-item--${n.type}${n.viewed_at ? '' : ' notif-item--new'}`}>
              <button className="notif-item__main" onClick={() => open(n)}>
                <span className="notif-item__icon" aria-hidden>
                  {n.type === 'task' ? '☐' : '•'}
                </span>
                <span className="notif-item__text">
                  <span className="notif-item__title">{text.title}</span>
                  {text.body && <span className="notif-item__body">{text.body}</span>}
                </span>
              </button>
              <button
                className="icon-button notif-item__action"
                onClick={() => act(n)}
                aria-label={n.type === 'task' ? t('notif.complete') : t('notif.dismiss')}
                title={n.type === 'task' ? t('notif.complete') : t('notif.dismiss')}
              >
                {n.type === 'task' ? '✓' : '✕'}
              </button>
            </div>
          );
        })}
        <Link to="/notifications" className="notif-bar__all">
          {t('notif.seeAll')}
        </Link>
      </div>
    </section>
  );
}
