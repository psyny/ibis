import { ReactNode, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useNotificationBar } from '../hooks/useNotifications';
import { useI18n } from '../i18n';
import { NotificationBar } from './NotificationBar';

interface TopBarProps {
  householdId?: string;
  householdName?: string;
  canManage?: boolean;
  /** The inbox page lists everything already, so it hides the bar */
  hideNotificationBar?: boolean;
  /** Extra controls, e.g. the month switcher */
  children?: ReactNode;
}

export function TopBar({ householdId, householdName, canManage, hideNotificationBar, children }: TopBarProps) {
  const { me, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { t, tn } = useI18n();
  const notifications = useNotificationBar(!!me);
  const unviewed = notifications?.unviewed_count || 0;

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [open]);

  const go = (path: string) => {
    setOpen(false);
    navigate(path);
  };

  const otherHouseholds = (me?.households || []).filter((h) => h.id !== householdId);

  return (
    <>
    <header className="topbar">
      <Link to={householdId ? `/h/${householdId}` : '/'} className="topbar__brand" title={t('menu.monthlyCosts')}>
        <img src="/favicon.svg" width={26} height={26} alt="" />
        Ibis
        {householdName && <span className="topbar__household">· {householdName}</span>}
      </Link>
      <div className="topbar__spacer" />
      {children}
      <div className="menu" ref={menuRef}>
        <button
          className="icon-button menu__toggle"
          onClick={() => setOpen((v) => !v)}
          aria-label={unviewed > 0 ? `${t('menu.aria')} (${tn('notif.newCount', unviewed)})` : t('menu.aria')}
          aria-expanded={open}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="4" y1="7" x2="20" y2="7" />
            <line x1="4" y1="12" x2="20" y2="12" />
            <line x1="4" y1="17" x2="20" y2="17" />
          </svg>
          {unviewed > 0 && <span className="menu__dot" aria-hidden />}
        </button>
        {open && (
          <nav className="menu__panel">
            <div className="menu__label">{me ? t('menu.signedInAs', { name: me.display_name }) : t('menu.notSignedIn')}</div>
            {householdId && (
              <button className="menu__item" onClick={() => go(`/h/${householdId}`)}>
                {t('menu.monthlyCosts')}
              </button>
            )}
            {householdId && canManage && (
              <button className="menu__item" onClick={() => go(`/h/${householdId}/settings`)}>
                {t('menu.householdSettings')}
              </button>
            )}
            <button className="menu__item menu__item--count" onClick={() => go('/notifications')}>
              <span>{t('menu.notifications')}</span>
              {unviewed > 0 && <span className="count-badge">{unviewed}</span>}
            </button>
            <button className="menu__item" onClick={() => go('/account')}>
              {t('menu.myAccount')}
            </button>
            <button className="menu__item" onClick={() => go('/tools')}>
              {t('menu.tools')}
            </button>
            {me?.is_admin && (
              <button className="menu__item" onClick={() => go('/admin')}>
                {t('menu.admin')}
              </button>
            )}
            {otherHouseholds.length > 0 && (
              <>
                <div className="menu__separator" />
                <div className="menu__label">{t('menu.switchHousehold')}</div>
                {otherHouseholds.map((h) => (
                  <button key={h.id} className="menu__item" onClick={() => go(`/h/${h.id}`)}>
                    {h.name}
                  </button>
                ))}
              </>
            )}
            <div className="menu__separator" />
            {me ? (
              <button className="menu__item" onClick={signOut}>
                {t('menu.signOut')}
              </button>
            ) : (
              <button className="menu__item" onClick={() => go('/login')}>
                {t('menu.signIn')}
              </button>
            )}
          </nav>
        )}
      </div>
    </header>
    {!hideNotificationBar && notifications && <NotificationBar items={notifications.items} />}
    </>
  );
}
