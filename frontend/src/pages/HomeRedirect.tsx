import { Navigate } from 'react-router-dom';
import { TopBar } from '../components/TopBar';
import { lastHousehold, useAuth } from '../contexts/AuthContext';

/** Sends the user to their last (or first) household. */
export function HomeRedirect() {
  const { me } = useAuth();
  const households = me?.households || [];
  const remembered = lastHousehold();
  const target = households.find((h) => h.id === remembered) || households[0];

  if (target) return <Navigate to={`/h/${target.id}`} replace />;
  if (me?.is_admin) return <Navigate to="/admin" replace />;

  return (
    <>
      <TopBar />
      <div className="page">
        <div className="page__inner page__inner--narrow">
          <div className="card state-message">
            You are not part of any household yet.
            <div className="state-message__sub">Ask a household manager or the app admin to add you.</div>
          </div>
        </div>
      </div>
    </>
  );
}
