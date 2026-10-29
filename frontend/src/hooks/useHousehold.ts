import { useCallback, useEffect, useState } from 'react';
import { getHousehold } from '../api/households';
import type { Household } from '../api/types';
import { rememberHousehold } from '../contexts/AuthContext';

export function useHousehold(householdId: string | undefined) {
  const [household, setHousehold] = useState<Household | null>(null);
  const [error, setError] = useState('');

  const reload = useCallback(async () => {
    if (!householdId) return;
    try {
      const data = await getHousehold(householdId);
      setHousehold(data);
      setError('');
      rememberHousehold(data.id);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [householdId]);

  useEffect(() => {
    setHousehold(null);
    reload();
  }, [reload]);

  return { household, error, reload };
}
