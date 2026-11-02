import { useEffect, useState } from 'react';
import { getMember } from '../api/households';
import type { MemberDetail } from '../api/types';
import { useMessage } from '../contexts/MessageContext';
import { MessageKey, useI18n } from '../i18n';
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
  const { t } = useI18n();

  useEffect(() => {
    getMember(householdId, memberId)
      .then(setMember)
      .catch((e: Error) => setError(e.message));
  }, [householdId, memberId]);

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      showMessage('success', t('common.copied'));
    } catch {
      showMessage('error', t('common.copyFailed'));
    }
  };

  const whatsappDigits = member?.whatsapp?.replace(/\D/g, '');
  const hasAnything = member && (member.email || member.whatsapp || member.bank_info || member.transfer_qr);

  return (
    <Modal title={member?.display_name || t('contact.member')} onClose={onClose}>
      {error && <p className="form-error">{error}</p>}
      {!member && !error && <p className="muted">{t('common.loading')}</p>}
      {member && (
        <div className="contact-list">
          <p className="muted small">
            {t(`role.${member.role}` as MessageKey)}
            {!member.is_active && ` · ${t('contact.disabled')}`}
          </p>
          {!hasAnything && <p className="muted">{t('contact.empty')}</p>}
          {member.bank_info && (
            <div className="contact-row">
              <div className="grow">
                <div className="contact-row__label">{member.bank_info_type === 'pix' ? t('pix.keyLabel') : t('bank.label')}</div>
                <div className="contact-row__value">{member.bank_info}</div>
              </div>
              <button className="button button--secondary button--small" onClick={() => copy(member.bank_info!)}>
                {t('common.copy')}
              </button>
            </div>
          )}
          {member.whatsapp && (
            <div className="contact-row">
              <div className="grow">
                <div className="contact-row__label">{t('common.whatsapp')}</div>
                <div className="contact-row__value">{member.whatsapp}</div>
              </div>
              {whatsappDigits && (
                <a className="button button--secondary button--small" href={`https://wa.me/${whatsappDigits}`} target="_blank" rel="noreferrer">
                  {t('contact.openWhatsapp')}
                </a>
              )}
            </div>
          )}
          {member.email && (
            <div className="contact-row">
              <div className="grow">
                <div className="contact-row__label">{t('common.email')}</div>
                <div className="contact-row__value">{member.email}</div>
              </div>
              <a className="button button--secondary button--small" href={`mailto:${member.email}`}>
                {t('contact.sendEmail')}
              </a>
            </div>
          )}
          {member.transfer_qr && (
            <div>
              <div className="contact-row__label">{t('contact.qr')}</div>
              <img className="qr-image" src={member.transfer_qr} alt={t('contact.qrAlt', { name: member.display_name })} />
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
