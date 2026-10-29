import { useEffect, useState } from 'react';
import { getMember } from '../api/households';
import type { MemberDetail } from '../api/types';
import { useMessage } from '../contexts/MessageContext';
import { ROLE_LABELS } from '../utils/format';
import { Modal } from './Modal';

interface Props {
  householdId: string;
  memberId: string;
  onClose: () => void;
}

/** Contact and payment info of a member: email, WhatsApp, bank info (PIX key or other) and QR code. */
export function MemberContactModal({ householdId, memberId, onClose }: Props) {
  const [member, setMember] = useState<MemberDetail | null>(null);
  const [error, setError] = useState('');
  const showMessage = useMessage();

  useEffect(() => {
    getMember(householdId, memberId)
      .then(setMember)
      .catch((e: Error) => setError(e.message));
  }, [householdId, memberId]);

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      showMessage('success', 'Copied');
    } catch {
      showMessage('error', 'Could not copy');
    }
  };

  const whatsappDigits = member?.whatsapp?.replace(/\D/g, '');
  const hasAnything = member && (member.email || member.whatsapp || member.bank_info || member.transfer_qr);

  return (
    <Modal title={member?.display_name || 'Member'} onClose={onClose}>
      {error && <p className="form-error">{error}</p>}
      {!member && !error && <p className="muted">Loading...</p>}
      {member && (
        <div className="contact-list">
          <p className="muted small">
            {ROLE_LABELS[member.role]}
            {!member.is_active && ' · disabled'}
          </p>
          {!hasAnything && <p className="muted">No contact or payment info yet.</p>}
          {member.bank_info && (
            <div className="contact-row">
              <div className="grow">
                <div className="contact-row__label">{member.bank_info_type === 'pix' ? 'PIX key' : 'Bank info'}</div>
                <div className="contact-row__value">{member.bank_info}</div>
              </div>
              <button className="button button--secondary button--small" onClick={() => copy(member.bank_info!)}>
                Copy
              </button>
            </div>
          )}
          {member.whatsapp && (
            <div className="contact-row">
              <div className="grow">
                <div className="contact-row__label">WhatsApp</div>
                <div className="contact-row__value">{member.whatsapp}</div>
              </div>
              {whatsappDigits && (
                <a className="button button--secondary button--small" href={`https://wa.me/${whatsappDigits}`} target="_blank" rel="noreferrer">
                  Open
                </a>
              )}
            </div>
          )}
          {member.email && (
            <div className="contact-row">
              <div className="grow">
                <div className="contact-row__label">Email</div>
                <div className="contact-row__value">{member.email}</div>
              </div>
              <a className="button button--secondary button--small" href={`mailto:${member.email}`}>
                Email
              </a>
            </div>
          )}
          {member.transfer_qr && (
            <div>
              <div className="contact-row__label">Transfer QR code</div>
              <img className="qr-image" src={member.transfer_qr} alt={`Transfer QR code of ${member.display_name}`} />
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
