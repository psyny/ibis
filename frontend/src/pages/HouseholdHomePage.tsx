import { Link, Navigate, useLocation, useParams } from 'react-router-dom';
import { MAIN_SECTIONS, OTHER_SECTIONS, Section } from '../components/sections';
import { TopBar } from '../components/TopBar';
import { useHousehold } from '../hooks/useHousehold';
import { useI18n } from '../i18n';

/** A household's home screen: cards for its sections. */
export function HouseholdHomePage() {
  const { householdId } = useParams();
  const { search } = useLocation();
  const { household, error } = useHousehold(householdId);
  const { t } = useI18n();

  if (!householdId) return null;
  // Older links (e.g. payment notifications) pointed here with ?m=YYYY-MM&pay=...: those are the costs screen
  const params = new URLSearchParams(search);
  if (params.has('m') || params.has('pay')) return <Navigate to={`/h/${householdId}/costs${search}`} replace />;

  const card = (section: Section, size: 'main' | 'small') => (
    <Link key={section.id} to={section.path(householdId)} className={`card hub-card hub-card--${size}`}>
      <span className="hub-card__icon">
        <section.Icon size={size === 'main' ? 32 : 24} />
      </span>
      <span className="hub-card__title">{t(section.title)}</span>
      <span className="hub-card__description">{t(section.description)}</span>
    </Link>
  );

  return (
    <>
      <TopBar householdId={householdId} householdName={household?.name} canManage={household?.permissions.can_manage} />
      <main className="page">
        <div className="page__inner">
          {error && <div className="card state-message">{error}</div>}
          {!error && (
            <>
              <h1 className="page-title">{household?.name || t('common.loading')}</h1>
              <div className="hub-grid hub-grid--main">{MAIN_SECTIONS.map((s) => card(s, 'main'))}</div>
              <div className="hub-divider" role="separator" />
              <div className="hub-grid hub-grid--small">{OTHER_SECTIONS.map((s) => card(s, 'small'))}</div>
            </>
          )}
        </div>
      </main>
    </>
  );
}
