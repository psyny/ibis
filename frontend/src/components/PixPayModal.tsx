import { useEffect, useMemo, useState } from 'react';
import { PixSVG } from 'react-qrcode-pix';
import { getMember } from '../api/households';
import type { Member } from '../api/types';
import { useMessage } from '../contexts/MessageContext';
import { formatMoney } from '../utils/format';
import { buildPix } from '../utils/pix';
import { Modal } from './Modal';

interface Props {
  householdId: string;
  payerName: string;
  receiver: Member;
  amount: number;
  currency: string;
  onClose: () => void;
}

/**
 * "Pay X" sheet: a PIX QR code (and copia-e-cola code) with the exact amount when the
 * receiver has a PIX key; otherwise their bank info and uploaded QR image.
 */
export function PixPayModal({ householdId, payerName, receiver, amount, currency, onClose }: Props) {
  const showMessage = useMessage();
  const [uploadedQr, setUploadedQr] = useState<string | null>(null);

  const hasPixKey = receiver.bank_info_type === 'pix' && !!receiver.bank_info;
  const isBRL = currency.toUpperCase() === 'BRL';

  const pix = useMemo(() => {
    if (!hasPixKey || !isBRL) return null;
    try {
      return { data: buildPix(receiver.bank_info!, receiver.display_name, amount), error: '' };
    } catch (e) {
      return { data: null, error: (e as Error).message };
    }
  }, [hasPixKey, isBRL, receiver.bank_info, receiver.display_name, amount]);

  // Fall back to the image the person uploaded when we can't generate a PIX code
  useEffect(() => {
    if (pix?.data || !receiver.has_transfer_qr) return;
    getMember(householdId, receiver.id)
      .then((m) => setUploadedQr(m.transfer_qr))
      .catch(() => setUploadedQr(null));
  }, [pix, householdId, receiver.id, receiver.has_transfer_qr]);

  const copy = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      showMessage('success', `${label} copied`);
    } catch {
      showMessage('error', 'Could not copy');
    }
  };

  return (
    <Modal title={`Pay ${receiver.display_name}`} onClose={onClose}>
      <p className="pay-amount num">{formatMoney(amount, currency)}</p>
      <p className="muted small" style={{ textAlign: 'center', marginBottom: 12 }}>
        {payerName} pays {receiver.display_name}
      </p>

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
          {receiver.bank_info ? (
            <div className="contact-row">
              <div className="grow">
                <div className="contact-row__label">{receiver.bank_info_type === 'pix' ? 'PIX key' : 'Bank info'}</div>
                <div className="contact-row__value">{receiver.bank_info}</div>
              </div>
              <button className="button button--secondary button--small" onClick={() => copy(receiver.bank_info!, 'Bank info')}>
                Copy
              </button>
            </div>
          ) : (
            !uploadedQr && <p className="muted">{receiver.display_name} hasn't added bank info yet.</p>
          )}
          {uploadedQr && (
            <div>
              <div className="contact-row__label">QR code from {receiver.display_name}</div>
              <img className="qr-image" src={uploadedQr} alt={`Payment QR code of ${receiver.display_name}`} />
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
