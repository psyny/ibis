import { request } from './config';
import type { AppNotification, NotificationBarData, NotificationBox } from './types';

const base = '/api/notifications';

export const listNotifications = (box: NotificationBox) => request<AppNotification[]>(`${base}?box=${box}`);
export const getNotificationBar = () => request<NotificationBarData>(`${base}/bar`);

const action = (name: string) => (id: string) => request<AppNotification>(`${base}/${id}/${name}`, { method: 'POST' });
export const viewNotification = action('view');
export const deleteNotification = action('delete');
export const restoreNotification = action('restore');
