import { ReactNode, useState } from 'react';
import { Modal } from './Modal';

interface Props {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  danger?: boolean;
  onConfirm: () => Promise<void> | void;
  onClose: () => void;
}

/** Asks "are you sure?" before an action. Closes itself after the action succeeds. */
export function ConfirmModal({ title, children, confirmLabel, danger, onConfirm, onClose }: Props) {
  const [busy, setBusy] = useState(false);

  const confirm = async () => {
    setBusy(true);
    try {
      await onConfirm();
      onClose();
    } catch {
      // onConfirm shows its own error message; keep the dialog open so the user can retry
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={title} onClose={onClose}>
      <div className="muted">{children}</div>
      <div className="modal__actions">
        <button className="button button--ghost" onClick={onClose} disabled={busy}>
          Cancel
        </button>
        <button className={`button ${danger ? 'button--danger' : 'button--primary'}`} onClick={confirm} disabled={busy}>
          {busy ? 'Working...' : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
