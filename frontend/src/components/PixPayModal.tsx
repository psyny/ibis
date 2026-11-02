import { useEffect, useMemo, useRef, useState } from 'react';
import { PixSVG } from 'react-qrcode-pix';
import type { BankInfoType } from '../api/types';
import { useMessage } from '../contexts/MessageContext';
import { formatMoney } from '../utils/format';
import { buildPix } from '../utils/pix';
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
  const [uploadedQr, setUploadedQr] = useState<string | null>(receiver.uploadedQr ?? null);

  const hasPixKey = receiver.bankInfoType === 'pix' && !!receiver.bankInfo;
  const isBRL = currency.toUpperCase() === 'BRL';

  const pix = useMemo(() => {
    if (!hasPixKey || !isBRL) return null;
    try {
      return { data: buildPix(receiver.bankInfo!, receiver.name, amount), error: '' };
    } catch (e) {
      return { data: null, error: (e as Error).message };
    }
  }, [hasPixKey, isBRL, receiver.bankInfo, receiver.name, amount]);

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

  const copy = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      showMessage('success', `${label} copied`);
    } catch {
      showMessage('error', 'Could not copy');
    }
  };

  return (
    <Modal title={`Pay ${receiver.name}`} onClose={onClose}>
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
            Scan with your bank app, or copy the PIX code and paste it in “Pix Copia e Cola”.
          </p>
          <div className="row" style={{ justifyContent: 'center' }}>
            <button className="button button--primary" onClick={() => copy(pix.data!.code, 'PIX code')}>
              Copy PIX code
            </button>
            <button className="button button--secondary" onClick={() => copy(pix.data!.pixkey, 'PIX key')}>
              Copy key
            </button>
          </div>
          <p className="muted small" style={{ textAlign: 'center', marginTop: 10, wordBreak: 'break-all' }}>
            Key: {pix.data.pixkey}
          </p>
        </>
      )}

      {!pix?.data && (
        <div className="contact-list">
          {pix?.error && <div className="banner banner--warning">{pix.error}</div>}
          {hasPixKey && !isBRL && (
            <div className="banner">PIX QR codes need the household currency to be BRL. Here is the key:</div>
          )}
          {receiver.bankInfo ? (
            <div className="contact-row">
              <div className="grow">
                <div className="contact-row__label">{receiver.bankInfoType === 'pix' ? 'PIX key' : 'Bank info'}</div>
                <div className="contact-row__value">{receiver.bankInfo}</div>
              </div>
              <button className="button button--secondary button--small" onClick={() => copy(receiver.bankInfo!, 'Bank info')}>
                Copy
              </button>
            </div>
          ) : (
            !uploadedQr && <p className="muted">{receiver.name} hasn't added bank info yet.</p>
          )}
          {uploadedQr && (
            <div>
              <div className="contact-row__label">QR code from {receiver.name}</div>
              <img className="qr-image" src={uploadedQr} alt={`Payment QR code of ${receiver.name}`} />
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
