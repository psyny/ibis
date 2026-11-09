import { useParams, useSearchParams } from 'react-router-dom';
import { CategoriesSection, PresetsSection } from '../components/settings/CatalogSection';
import { GeneralSection } from '../components/settings/GeneralSection';
import { MembersSection } from '../components/settings/MembersSection';
import { MonthsSection } from '../components/settings/MonthsSection';
import { RecurringSection } from '../components/settings/RecurringSection';
import { TaskLabelsSection } from '../components/settings/TaskLabelsSection';
import { TopBar } from '../components/TopBar';
import { useHousehold } from '../hooks/useHousehold';
import { MessageKey, useI18n } from '../i18n';

const TABS: { id: string; label: MessageKey }[] = [
  { id: 'members', label: 'settings.tab.members' },
  { id: 'categories', label: 'settings.tab.categories' },
  { id: 'descriptions', label: 'settings.tab.descriptions' },
  { id: 'starting', label: 'settings.tab.fixedCosts' },
  { id: 'months', label: 'settings.tab.months' },
  { id: 'tasks', label: 'settings.tab.tasks' },
  { id: 'general', label: 'settings.tab.general' },
];

/** Household settings, for managers (and app admins). */
export function SettingsPage() {
  const { householdId } = useParams();
  const [params, setParams] = useSearchParams();
  const { household, error, reload } = useHousehold(householdId);
  const { t } = useI18n();
  const tab = TABS.some((item) => item.id === params.get('tab')) ? params.get('tab')! : 'members';

  const content = () => {
    if (error) return <div className="card state-message">{error}</div>;
    if (!household) return <div className="state-message">{t('common.loading')}</div>;
    if (!household.permissions.can_manage) {
      return <div className="card state-message">{t('settings.onlyManagers')}</div>;
    }
    switch (tab) {
      case 'categories':
        return <CategoriesSection householdId={household.id} />;
      case 'descriptions':
        return <PresetsSection householdId={household.id} currency={household.currency} />;
      case 'starting':
        return <RecurringSection householdId={household.id} currency={household.currency} />;
      case 'months':
        return <MonthsSection householdId={household.id} currency={household.currency} />;
      case 'tasks':
        return <TaskLabelsSection householdId={household.id} />;
      case 'general':
        return <GeneralSection key={household.id} household={household} onSaved={reload} />;
      default:
        return <MembersSection householdId={household.id} />;
    }
  };

  return (
    <>
      <TopBar householdId={householdId} householdName={household?.name} canManage={household?.permissions.can_manage} />
      <main className="page">
        <div className="page__inner">
          <div>
            <h1 className="page-title">{t('settings.title')}</h1>
            <p className="page-description">{household?.name}</p>
          </div>
          {household?.permissions.can_manage && (
            <nav className="tabs" aria-label={t('settings.sections')}>
              {TABS.map((item) => (
                <button key={item.id} className={`tab ${tab === item.id ? 'tab--active' : ''}`} onClick={() => setParams({ tab: item.id })}>
                  {t(item.label)}
                </button>
              ))}
            </nav>
          )}
          {content()}
        </div>
      </main>
    </>
  );
}
