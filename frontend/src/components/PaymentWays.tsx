import { useMessage } from '../contexts/MessageContext';
import { useI18n } from '../i18n';
import type { MonthPaymentData } from '../utils/notifications';
import { paymentPageUrl } from '../utils/pix';

/**
 * The ways to pay a month's transfer, as saved at the close: a direct transfer (PIX key or bank
 * details), the public Ibis payment page and the PIX copy-and-paste code. WhatsApp reminders list
 * the same (backend domain/messages.py payment_message).
 */
export function PaymentWays({ payment }: { payment: MonthPaymentData }) {
  const { t, lang } = useI18n();
  const showMessage = useMessage();
  const { pix_key: key, pix_code: code, bank_info: bank } = payment;
  const page = key && code ? paymentPageUrl(key, payment.to_name, payment.amount, lang) : null;

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      showMessage('success', t('common.copied'));
    } catch {
      showMessage('error', t('common.copyFailed'));
    }
  };

  const ways = [
    key && { label: t('task.monthPayment.key'), value: key },
    !key && bank && { label: t('task.monthPayment.bank'), value: bank },
    page && { label: t('task.monthPayment.page'), value: page, open: page },
    code && { label: t('task.monthPayment.code'), value: code },
  ].filter(Boolean) as { label: string; value: string; open?: string }[];

  if (!ways.length) {
    return <p className="muted small payment-ways">{t('task.monthPayment.none', { name: payment.to_name })}</p>;
  }
  return (
    <div className="payment-ways">
      <p className="small">{t('task.monthPayment.ways')}</p>
      <ol className="contact-list">
        {ways.map((way, i) => (
          <li key={way.label} className="contact-row">
            <div className="grow">
              <div className="contact-row__label">
                {i + 1}) {way.label}
              </div>
              <div className="contact-row__value payment-ways__value">{way.value}</div>
            </div>
            {way.open && (
              <a className="button button--secondary button--small" href={way.open} target="_blank" rel="noreferrer">
                {t('task.monthPayment.open')}
              </a>
            )}
            <button className="button button--secondary button--small" onClick={() => copy(way.value)}>
              {t('common.copy')}
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
