import { ReactNode, useEffect, useRef, useState } from 'react';

interface Props {
  /** The button's icon */
  icon: ReactNode;
  /** Accessible name of the button */
  label: string;
  title?: string;
  /** Menu content; call `close` before running an item's action */
  children: (close: () => void) => ReactNode;
}

/** A page's actions in the top bar's right side (e.g. month actions, task actions). */
export function ActionsMenu({ icon, label, title, children }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

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

  return (
    <div className="menu" ref={ref}>
      <button className="icon-button" onClick={() => setOpen((v) => !v)} aria-label={label} aria-expanded={open} title={title}>
        {icon}
      </button>
      {open && <nav className="menu__panel">{children(() => setOpen(false))}</nav>}
    </div>
  );
}
