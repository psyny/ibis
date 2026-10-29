import { useEffect, useRef, useState } from 'react';
import type { MonthInfo } from '../api/types';
import { monthLabel } from '../utils/format';

interface Props {
  month: MonthInfo;
  onClose: () => void;
  onReopen: () => void;
  /** Resolves when done; the menu item stays disabled meanwhile so it can't run twice */
  onAddFixedCosts: () => Promise<void>;
}

/** Manager/admin actions for the month on screen (top bar, left of the main menu). */
export function MonthActionsMenu({ month, onClose, onReopen, onAddFixedCosts }: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const label = monthLabel(month.year, month.month);
  const isOpen = month.status === 'open';

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const run = (action: () => void) => {
    setOpen(false);
    action();
  };

  const addFixed = async () => {
    if (busy) return;
    setBusy(true);
    setOpen(false);
    try {
      await onAddFixedCosts();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="menu" ref={ref}>
      <button
        className="icon-button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Actions for ${label}`}
        aria-expanded={open}
        title="Month actions"
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="4" width="18" height="17" rx="2" />
          <line x1="3" y1="9" x2="21" y2="9" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="16" y1="2" x2="16" y2="6" />
          {isOpen ? <path d="M8.5 15h7M12 11.5v7" /> : <path d="M9 15l2 2 4-4" />}
        </svg>
      </button>
      {open && (
        <nav className="menu__panel">
          <div className="menu__label">
            {label} · {isOpen ? 'open' : 'closed'}
          </div>
          {isOpen ? (
            <>
              <button className="menu__item" onClick={addFixed} disabled={busy}>
                {busy ? 'Adding fixed costs...' : 'Add fixed costs'}
                <span className="menu__hint">Adds missing ones, never duplicates</span>
              </button>
              <button className="menu__item" onClick={() => run(onClose)}>
                Close month
                <span className="menu__hint">No more cost changes</span>
              </button>
            </>
          ) : (
            <button className="menu__item" onClick={() => run(onReopen)}>
              Reopen month
            </button>
          )}
        </nav>
      )}
    </div>
  );
}
