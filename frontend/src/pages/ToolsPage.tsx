import { Link } from 'react-router-dom';
import { TopBar } from '../components/TopBar';
import { lastHousehold, useAuth } from '../contexts/AuthContext';
import { MessageKey, useI18n } from '../i18n';

interface Tool {
  path: string;
  icon: string;
  title: MessageKey;
  description: MessageKey;
}

/** Add new tools here: each one becomes a card on /tools. */
const TOOLS: Tool[] = [
  {
    path: '/tools/pixgen',
    icon: '⚡',
    title: 'pixgen.title',
    description: 'pixgen.description',
  },
];

export function ToolsPage() {
  const { me } = useAuth();
  const { t } = useI18n();
  const householdId = lastHousehold() || me?.households[0]?.id;
  const household = me?.households.find((h) => h.id === householdId);

  return (
    <>
      <TopBar householdId={householdId} householdName={household?.name} canManage={household?.role === 'manager' || me?.is_admin} />
      <main className="page">
        <div className="page__inner">
          <div>
            <h1 className="page-title">{t('tools.title')}</h1>
            <p className="page-description">{t('tools.description')}</p>
          </div>
          <div className="tools-grid">
            {TOOLS.map((tool) => (
              <Link key={tool.path} to={tool.path} className="card tool-card">
                <span className="tool-card__icon" aria-hidden>
                  {tool.icon}
                </span>
                <span className="tool-card__title">{t(tool.title)}</span>
                <span className="tool-card__description">{t(tool.description)}</span>
              </Link>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
