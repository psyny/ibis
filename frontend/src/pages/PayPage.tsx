import { useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { PixPaySheet } from '../components/PixPayModal';
import { hasChosenLanguage, isLanguageCode, useI18n } from '../i18n';

/**
 * Public payment page: /pay?key=<PIX key>&name=<receiver>&amount=<30.00>&lang=<language>.
 * Shows the QR code and copy code for that transfer, with no sign-in, so it can be linked from
 * WhatsApp (see domain/pix.py payment_page_url). Everything comes from the link; nothing is loaded.
 */
export function PayPage() {
  const [params] = useSearchParams();
  const { t, setLang } = useI18n();
  const key = (params.get('key') || '').trim();
  const name = (params.get('name') || '').trim();
  const amount = Number(params.get('amount'));
  const valid = !!key && Number.isFinite(amount) && amount > 0 && amount < 1_000_000_000;

  // Open in the household's language, unless this browser already has one picked
  const lang = params.get('lang');
  useEffect(() => {
    if (isLanguageCode(lang) && !hasChosenLanguage()) setLang(lang);
  }, [lang, setLang]);

  return (
    <div className="login-page">
      <div className="card login-card">
        <img src="/favicon.svg" width={40} height={40} alt="" style={{ display: 'block', margin: '0 auto 8px' }} />
        {valid ? (
          <>
            <h1 className="login-card__title" style={{ fontSize: 22, marginBottom: 4 }}>
              {t('pay.title', { name: name || '?' })}
            </h1>
            <PixPaySheet
              receiver={{ name: name || 'RECEBEDOR', bankInfoType: 'pix', bankInfo: key }}
              amount={Math.round(amount * 100) / 100}
              currency="BRL"
            />
          </>
        ) : (
          <p className="state-message">{t('payPage.invalid')}</p>
        )}
        <Link to="/" className="button button--ghost button--block" style={{ marginTop: 20 }}>
          {t('payPage.openIbis')}
        </Link>
      </div>
    </div>
  );
}
