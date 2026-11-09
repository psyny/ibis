import type { ComponentType } from 'react';
import type { MessageKey } from '../i18n';
import { AccountIcon, BellIcon, CostsIcon, TasksIcon, ToolsIcon } from './icons';

export interface Section {
  id: string;
  Icon: ComponentType<{ size?: number }>;
  title: MessageKey;
  description: MessageKey;
  /** Where it goes (household sections need the household id) */
  path: (householdId: string) => string;
}

/** The household's main screens: cards on the home screen and icons in the middle of the top bar. */
export const MAIN_SECTIONS: Section[] = [
  {
    id: 'costs',
    Icon: CostsIcon,
    title: 'nav.costs',
    description: 'hub.costs.description',
    path: (hid) => `/h/${hid}/costs`,
  },
  {
    id: 'tasks',
    Icon: TasksIcon,
    title: 'nav.tasks',
    description: 'hub.tasks.description',
    path: (hid) => `/h/${hid}/tasks`,
  },
];

/** Shown below the main cards on the home screen (and in the top bar's menu). */
export const OTHER_SECTIONS: Section[] = [
  { id: 'tools', Icon: ToolsIcon, title: 'menu.tools', description: 'hub.tools.description', path: () => '/tools' },
  {
    id: 'notifications',
    Icon: BellIcon,
    title: 'menu.notifications',
    description: 'hub.notifications.description',
    path: () => '/notifications',
  },
  { id: 'account', Icon: AccountIcon, title: 'menu.myAccount', description: 'hub.account.description', path: () => '/account' },
];

/** Which main section a path belongs to (adding/editing a cost counts as Costs). */
export function activeSection(pathname: string, householdId: string): string | null {
  const base = `/h/${householdId}`;
  if (pathname.startsWith(`${base}/costs`) || pathname.startsWith(`${base}/add`)) return 'costs';
  if (pathname.startsWith(`${base}/tasks`)) return 'tasks';
  return null;
}
