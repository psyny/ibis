import { useEffect, useMemo, useRef, useState } from 'react';
import { PixSVG } from 'react-qrcode-pix';
import type { BankInfoType } from '../api/types';
import { useMessage } from '../contexts/MessageContext';
import { formatMoney } from '../utils/format';
import { useI18n } from '../i18n';
import { buildPix, PixKeyError } from '../utils/pix';
import { pixErrorText } from './BankInfoFields';
import { Modal } from './Modal';

/** Who gets the money. Works for a household member or for the signed-in user. */
export interface PixReceiver {
  name: string;
  bankInfoType: BankInfoType;
  bankInfo: string | null;
  /** Uploaded payment QR image, if already at hand */
  uploadedQr?: string | null;
  /** Or a way to fetch it, used only when no PIX code can be generated */
  loadUploadedQr?: () => Promise<string | null>;
}

interface Props {
  receiver: PixReceiver;
  amount: number;
  currency: string;
  /** Line under the amount, e.g. "Carla pays Ana" */
  subtitle?: string;
  onClose: () => void;
}

/**
 * "Pay X" sheet: a PIX QR code (and copia-e-cola code) with the exact amount when the
 * receiver has a PIX key; otherwise their bank info and uploaded QR image.
 * Used by the split table and by the PIX code generator tool.
 */
export function PixPayModal({ receiver, amount, currency, subtitle, onClose }: Props) {
  const showMessage = useMessage();
  const { t } = useI18n();
  const [uploadedQr, setUploadedQr] = useState<string | null>(receiver.uploadedQr ?? null);

  const hasPixKey = receiver.bankInfoType === 'pix' && !!receiver.bankInfo;
  const isBRL = currency.toUpperCase() === 'BRL';

  const pix = useMemo(() => {
    if (!hasPixKey || !isBRL) return null;
    try {
      return { data: buildPix(receiver.bankInfo!, receiver.name, amount), error: '' };
    } catch (e) {
      const message = e instanceof PixKeyError ? pixErrorText(t, e.code, e.params) : (e as Error).message;
      return { data: null, error: message };
    }
  }, [hasPixKey, isBRL, receiver.bankInfo, receiver.name, amount, t]);

  // Fall back to the image the person uploaded when we can't generate a PIX code
  const { loadUploadedQr } = receiver;
  const triedLoading = useRef(false);
  useEffect(() => {
    if (pix?.data || uploadedQr || !loadUploadedQr || triedLoading.current) return;
    triedLoading.current = true;
    loadUploadedQr()
      .then(setUploadedQr)
      .catch(() => setUploadedQr(null));
  }, [pix, uploadedQr, loadUploadedQr]);

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      showMessage('success', t('common.copied'));
    } catch {
      showMessage('error', t('common.copyFailed'));
    }
  };

  return (
    <Modal title={t('pay.title', { name: receiver.name })} onClose={onClose}>
      <p className="pay-amount num">{formatMoney(amount, currency)}</p>
      {subtitle && (
        <p className="muted small" style={{ textAlign: 'center', marginBottom: 12 }}>
          {subtitle}
        </p>
      )}

      {pix?.data && (
        <>
          <div className="pix-qr">
            <PixSVG
              pixkey={pix.data.pixkey}
              merchant={pix.data.merchant}
              city={pix.data.city}
              amount={pix.data.amount}
              size={220}
              padding={12}
              color="#000000"
              bgColor="#ffffff"
              bgRounded
              level="M"
            />
          </div>
          <p className="muted small" style={{ textAlign: 'center', margin: '10px 0' }}>
            {t('pay.scanHint')}
          </p>
          <div className="row" style={{ justifyContent: 'center' }}>
            <button className="button button--primary" onClick={() => copy(pix.data!.code)}>
              {t('pay.copyCode')}
            </button>
            <button className="button button--secondary" onClick={() => copy(pix.data!.pixkey)}>
              {t('pay.copyKey')}
            </button>
          </div>
          <p className="muted small" style={{ textAlign: 'center', marginTop: 10, wordBreak: 'break-all' }}>
            {t('pay.key', { key: pix.data.pixkey })}
          </p>
        </>
      )}

      {!pix?.data && (
        <div className="contact-list">
          {pix?.error && <div className="banner banner--warning">{pix.error}</div>}
          {hasPixKey && !isBRL && (
            <div className="banner">{t('pay.needsBRL')}</div>
          )}
          {receiver.bankInfo ? (
            <div className="contact-row">
              <div className="grow">
                <div className="contact-row__label">{receiver.bankInfoType === 'pix' ? t('pix.keyLabel') : t('bank.label')}</div>
                <div className="contact-row__value">{receiver.bankInfo}</div>
              </div>
              <button className="button button--secondary button--small" onClick={() => copy(receiver.bankInfo!)}>
                {t('common.copy')}
              </button>
            </div>
          ) : (
            !uploadedQr && <p className="muted">{t('pay.noBankInfo', { name: receiver.name })}</p>
          )}
          {uploadedQr && (
            <div>
              <div className="contact-row__label">{t('pay.qrFrom', { name: receiver.name })}</div>
              <img className="qr-image" src={uploadedQr} alt={t('contact.qrAlt', { name: receiver.name })} />
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
