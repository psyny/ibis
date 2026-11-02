import { useCallback, useEffect, useState } from 'react';
import { getHousehold } from '../api/households';
import type { Household } from '../api/types';
import { rememberHousehold } from '../contexts/AuthContext';
import { useI18n } from '../i18n';

export function useHousehold(householdId: string | undefined) {
  const [household, setHousehold] = useState<Household | null>(null);
  const [error, setError] = useState('');
  const { setLang } = useI18n();

  const reload = useCallback(async () => {
    if (!householdId) return;
    try {
      const data = await getHousehold(householdId);
      setHousehold(data);
      setError('');
      rememberHousehold(data.id);
      setLang(data.language); // the whole interface follows the household's language
    } catch (e) {
      setError((e as Error).message);
    }
  }, [householdId, setLang]);

  useEffect(() => {
    setHousehold(null);
    reload();
  }, [reload]);

  return { household, error, reload };
}
