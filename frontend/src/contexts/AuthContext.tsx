import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react';
import { getMe } from '../api/auth';
import { clearToken, getToken } from '../api/config';
import type { Me } from '../api/types';

const LAST_HOUSEHOLD_KEY = 'ibis_last_household';

interface AuthContextType {
  me: Me | null;
  loading: boolean;
  refresh: () => Promise<Me | null>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setMe(null);
      setLoading(false);
      return null;
    }
    try {
      const user = await getMe();
      setMe(user);
      return user;
    } catch {
      setMe(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const signOut = useCallback(() => {
    clearToken();
    setMe(null);
    window.location.href = '/login';
  }, []);

  return <AuthContext.Provider value={{ me, loading, refresh, signOut }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}

export function rememberHousehold(id: string) {
  localStorage.setItem(LAST_HOUSEHOLD_KEY, id);
}

export function lastHousehold(): string | null {
  return localStorage.getItem(LAST_HOUSEHOLD_KEY);
}
