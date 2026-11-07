import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getNotificationBar, viewNotification } from '../api/notifications';
import type { AppNotification, NotificationBarData } from '../api/types';
import { notificationLink, notificationsChanged, onNotificationsChanged } from '../utils/notifications';

const REFRESH_MS = 60_000;

/** The bar's items and the unviewed count. Reloads every minute, on window focus and on changes. */
export function useNotificationBar(enabled: boolean): NotificationBarData | null {
  const [data, setData] = useState<NotificationBarData | null>(null);

  useEffect(() => {
    if (!enabled) {
      setData(null);
      return;
    }
    let cancelled = false;
    const load = () =>
      getNotificationBar()
        .then((next) => !cancelled && setData(next))
        .catch(() => undefined); // the bar is optional; never break the page over it
    load();
    const timer = window.setInterval(load, REFRESH_MS);
    window.addEventListener('focus', load);
    const stop = onNotificationsChanged(load);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener('focus', load);
      stop();
    };
  }, [enabled]);

  return data;
}

/** Clicking a notification: mark it viewed, then go where it points (e.g. the payment sheet). */
export function useOpenNotification() {
  const navigate = useNavigate();
  return useCallback(
    async (n: AppNotification) => {
      if (!n.viewed_at) {
        try {
          await viewNotification(n.id);
        } catch {
          // still open it
        }
        notificationsChanged();
      }
      const link = notificationLink(n);
      if (link) navigate(link);
    },
    [navigate],
  );
}
