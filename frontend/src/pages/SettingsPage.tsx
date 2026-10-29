import { useParams, useSearchParams } from 'react-router-dom';
import { CategoriesSection, PresetsSection } from '../components/settings/CatalogSection';
import { GeneralSection } from '../components/settings/GeneralSection';
import { MembersSection } from '../components/settings/MembersSection';
import { MonthsSection } from '../components/settings/MonthsSection';
import { RecurringSection } from '../components/settings/RecurringSection';
import { TopBar } from '../components/TopBar';
import { useHousehold } from '../hooks/useHousehold';

const TABS = [
  { id: 'members', label: 'Members' },
  { id: 'categories', label: 'Categories' },
  { id: 'descriptions', label: 'Descriptions' },
  { id: 'starting', label: 'Fixed costs' },
  { id: 'months', label: 'Months' },
  { id: 'general', label: 'General' },
] as const;

/** Household settings, for managers (and app admins). */
export function SettingsPage() {
  const { householdId } = useParams();
  const [params, setParams] = useSearchParams();
  const { household, error, reload } = useHousehold(householdId);
  const tab = TABS.some((t) => t.id === params.get('tab')) ? params.get('tab')! : 'members';

  const content = () => {
    if (error) return <div className="card state-message">{error}</div>;
    if (!household) return <div className="state-message">Loading...</div>;
    if (!household.permissions.can_manage) {
      return <div className="card state-message">Only managers can change household settings.</div>;
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
            <h1 className="page-title">Settings</h1>
            <p className="page-description">{household?.name}</p>
          </div>
          {household?.permissions.can_manage && (
            <nav className="tabs" aria-label="Settings sections">
              {TABS.map((t) => (
                <button key={t.id} className={`tab ${tab === t.id ? 'tab--active' : ''}`} onClick={() => setParams({ tab: t.id })}>
                  {t.label}
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
