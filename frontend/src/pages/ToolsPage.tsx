import { Link } from 'react-router-dom';
import { TopBar } from '../components/TopBar';
import { lastHousehold, useAuth } from '../contexts/AuthContext';

interface Tool {
  path: string;
  icon: string;
  title: string;
  description: string;
}

/** Add new tools here: each one becomes a card on /tools. */
const TOOLS: Tool[] = [
  {
    path: '/tools/pixgen',
    icon: '⚡',
    title: 'PIX code generator',
    description: 'Create a PIX QR code and copy-and-paste code for any amount.',
  },
];

export function ToolsPage() {
  const { me } = useAuth();
  const householdId = lastHousehold() || me?.households[0]?.id;
  const household = me?.households.find((h) => h.id === householdId);

  return (
    <>
      <TopBar householdId={householdId} householdName={household?.name} canManage={household?.role === 'manager' || me?.is_admin} />
      <main className="page">
        <div className="page__inner">
          <div>
            <h1 className="page-title">Tools</h1>
            <p className="page-description">Handy extras for your household.</p>
          </div>
          <div className="tools-grid">
            {TOOLS.map((tool) => (
              <Link key={tool.path} to={tool.path} className="card tool-card">
                <span className="tool-card__icon" aria-hidden>
                  {tool.icon}
                </span>
                <span className="tool-card__title">{tool.title}</span>
                <span className="tool-card__description">{tool.description}</span>
              </Link>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
