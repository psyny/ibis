import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { RequireAuth } from './components/RequireAuth';
import { AuthProvider } from './contexts/AuthContext';
import { MessageProvider } from './contexts/MessageContext';
import { AccountPage } from './pages/AccountPage';
import { AdminPage } from './pages/AdminPage';
import { CostFormPage } from './pages/CostFormPage';
import { DashboardPage } from './pages/DashboardPage';
import { HomeRedirect } from './pages/HomeRedirect';
import { LoginPage } from './pages/LoginPage';
import { PixGenPage } from './pages/PixGenPage';
import { SettingsPage } from './pages/SettingsPage';
import { ToolsPage } from './pages/ToolsPage';

function App() {
  return (
    <AuthProvider>
      <MessageProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<RequireAuth />}>
              <Route path="/" element={<HomeRedirect />} />
              <Route path="/h/:householdId" element={<DashboardPage />} />
              {/* Shareable link straight to the add-cost screen */}
              <Route path="/h/:householdId/add" element={<CostFormPage />} />
              <Route path="/h/:householdId/costs/:costId" element={<CostFormPage />} />
              <Route path="/h/:householdId/settings" element={<SettingsPage />} />
              <Route path="/account" element={<AccountPage />} />
              <Route path="/tools" element={<ToolsPage />} />
              <Route path="/tools/pixgen" element={<PixGenPage />} />
              <Route path="/admin" element={<AdminPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </MessageProvider>
    </AuthProvider>
  );
}

export default App;
