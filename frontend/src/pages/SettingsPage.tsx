import { useParams, useSearchParams } from 'react-router-dom';
import type { Household } from '../api/types';
import { CategoriesSection, PresetsSection } from '../components/settings/CatalogSection';
import { EmailSection } from '../components/settings/EmailSection';
import { GeneralSection } from '../components/settings/GeneralSection';
import { MembersSection } from '../components/settings/MembersSection';
import { MonthsSection } from '../components/settings/MonthsSection';
import { RecurringSection } from '../components/settings/RecurringSection';
import { TaskLabelsSection } from '../components/settings/TaskLabelsSection';
import { WhatsAppSection } from '../components/settings/WhatsAppSection';
import { TopBar } from '../components/TopBar';
import { useHousehold } from '../hooks/useHousehold';
import { MessageKey, useI18n } from '../i18n';

interface Tab {
  id: string;
  label: MessageKey;
  /** Sub-tabs shown inside the tab (the first one is the default) */
  subs?: { id: string; label: MessageKey }[];
}

const TABS: Tab[] = [
  { id: 'general', label: 'settings.tab.general' },
  { id: 'members', label: 'settings.tab.members' },
  { id: 'whatsapp', label: 'settings.tab.whatsapp' },
  { id: 'email', label: 'settings.tab.email' },
  {
    id: 'expenses',
    label: 'settings.tab.expenses',
    subs: [
      { id: 'categories', label: 'settings.tab.categories' },
      { id: 'descriptions', label: 'settings.tab.descriptions' },
      { id: 'fixed', label: 'settings.tab.fixedCosts' },
      { id: 'months', label: 'settings.tab.months' },
    ],
  },
  {
    id: 'tasks',
    label: 'settings.tab.tasks',
    subs: [
      { id: 'categories', label: 'settings.tab.taskCategories' },
      { id: 'locations', label: 'settings.tab.taskLocations' },
    ],
  },
];

/** Old ?tab= values (before the tabs were grouped), so saved links keep working. */
const OLD_TABS: Record<string, [string, string]> = {
  categories: ['expenses', 'categories'],
  descriptions: ['expenses', 'descriptions'],
  starting: ['expenses', 'fixed'],
  months: ['expenses', 'months'],
};

function SectionContent({ household, tab, sub, reload }: { household: Household; tab: string; sub: string; reload: () => void }) {
  const hid = household.id;
  switch (`${tab}/${sub}`) {
    case 'members/':
      return <MembersSection householdId={hid} />;
    case 'whatsapp/':
      return <WhatsAppSection householdId={hid} />;
    case 'email/':
      return <EmailSection />;
    case 'expenses/categories':
      return <CategoriesSection householdId={hid} />;
    case 'expenses/descriptions':
      return <PresetsSection householdId={hid} currency={household.currency} />;
    case 'expenses/fixed':
      return <RecurringSection householdId={hid} currency={household.currency} />;
    case 'expenses/months':
      return <MonthsSection householdId={hid} currency={household.currency} />;
    case 'tasks/categories':
      return <TaskLabelsSection householdId={hid} kind="category" />;
    case 'tasks/locations':
      return <TaskLabelsSection householdId={hid} kind="location" />;
    default:
      return <GeneralSection key={hid} household={household} onSaved={reload} />;
  }
}

/** Household settings, for managers (and app admins). */
export function SettingsPage() {
  const { householdId } = useParams();
  const [params, setParams] = useSearchParams();
  const { household, error, reload } = useHousehold(householdId);
  const { t } = useI18n();

  const [oldTab, oldSub] = OLD_TABS[params.get('tab') || ''] || [];
  const current = TABS.find((item) => item.id === (oldTab || params.get('tab'))) || TABS[0];
  const subs = current.subs || [];
  const sub = subs.find((item) => item.id === (oldSub || params.get('sub')))?.id || subs[0]?.id || '';

  const content = () => {
    if (error) return <div className="card state-message">{error}</div>;
    if (!household) return <div className="state-message">{t('common.loading')}</div>;
    if (!household.permissions.can_manage) {
      return <div className="card state-message">{t('settings.onlyManagers')}</div>;
    }
    return <SectionContent household={household} tab={current.id} sub={sub} reload={reload} />;
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
            <>
              <nav className="tabs" aria-label={t('settings.sections')}>
                {TABS.map((item) => (
                  <button
                    key={item.id}
                    className={`tab ${current.id === item.id ? 'tab--active' : ''}`}
                    onClick={() => setParams({ tab: item.id })}
                  >
                    {t(item.label)}
                  </button>
                ))}
              </nav>
              {subs.length > 0 && (
                <nav className="tabs tabs--sub" aria-label={t(current.label)}>
                  {subs.map((item) => (
                    <button
                      key={item.id}
                      className={`tab tab--sub ${sub === item.id ? 'tab--active' : ''}`}
                      onClick={() => setParams({ tab: current.id, sub: item.id })}
                    >
                      {t(item.label)}
                    </button>
                  ))}
                </nav>
              )}
            </>
          )}
          {content()}
        </div>
      </main>
    </>
  );
}
