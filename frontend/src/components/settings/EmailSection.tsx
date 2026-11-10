import { useI18n } from '../../i18n';

/** Placeholder until email sending is set up. Tasks can already ask for email notifications. */
export function EmailSection() {
  const { t } = useI18n();
  return (
    <section className="card">
      <h2 className="card__title" style={{ marginBottom: 6 }}>
        {t('settings.tab.email')}
      </h2>
      <p className="muted">{t('email.soon')}</p>
    </section>
  );
}
