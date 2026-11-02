import { ReactNode, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface TopBarProps {
  householdId?: string;
  householdName?: string;
  canManage?: boolean;
  /** Extra controls, e.g. the month switcher */
  children?: ReactNode;
}

export function TopBar({ householdId, householdName, canManage, children }: TopBarProps) {
  const { me, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

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
    <header className="topbar">
      <Link to={householdId ? `/h/${householdId}` : '/'} className="topbar__brand" title="Monthly costs">
        <img src="/favicon.svg" width={26} height={26} alt="" />
        Ibis
        {householdName && <span className="topbar__household">· {householdName}</span>}
      </Link>
      <div className="topbar__spacer" />
      {children}
      <div className="menu" ref={menuRef}>
        <button className="icon-button" onClick={() => setOpen((v) => !v)} aria-label="Menu" aria-expanded={open}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="4" y1="7" x2="20" y2="7" />
            <line x1="4" y1="12" x2="20" y2="12" />
            <line x1="4" y1="17" x2="20" y2="17" />
          </svg>
        </button>
        {open && (
          <nav className="menu__panel">
            <div className="menu__label">{me ? `Signed in as ${me.display_name}` : 'Not signed in'}</div>
            {householdId && (
              <button className="menu__item" onClick={() => go(`/h/${householdId}`)}>
                Monthly costs
              </button>
            )}
            {householdId && canManage && (
              <button className="menu__item" onClick={() => go(`/h/${householdId}/settings`)}>
                Household settings
              </button>
            )}
            <button className="menu__item" onClick={() => go('/account')}>
              My account
            </button>
            <button className="menu__item" onClick={() => go('/tools')}>
              Tools
            </button>
            {me?.is_admin && (
              <button className="menu__item" onClick={() => go('/admin')}>
                Admin
              </button>
            )}
            {otherHouseholds.length > 0 && (
              <>
                <div className="menu__separator" />
                <div className="menu__label">Switch household</div>
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
                Sign out
              </button>
            ) : (
              <button className="menu__item" onClick={() => go('/login')}>
                Sign in
              </button>
            )}
          </nav>
        )}
      </div>
    </header>
  );
}
