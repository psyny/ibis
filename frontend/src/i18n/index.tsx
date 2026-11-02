/**
 * Translations. One file per language in ./locales; English (en.ts) is the source and
 * every other language must define exactly the same keys (TypeScript checks it).
 *
 *   const { t, tn } = useI18n();
 *   t('dashboard.split.title')                 -> "Split"
 *   t('cost.addedToast', { name: 'Rent' })     -> "Added Rent"   ({name} placeholders)
 *   tn('dashboard.transfers', 3)               -> "3 transfers" (picks the _one/_other key)
 *
 * Dates, months and money are formatted with the same locale (see utils/format.ts).
 */
import { createContext, ReactNode, useCallback, useContext, useMemo, useState } from 'react';
import { setFormatLocale } from '../utils/format';
import { de } from './locales/de';
import { en, Messages } from './locales/en';
import { fr } from './locales/fr';
import { hi } from './locales/hi';
import { it } from './locales/it';
import { ja } from './locales/ja';
import { ko } from './locales/ko';
import { ptBR } from './locales/pt-BR';
import { zhCN } from './locales/zh-CN';

export type LanguageCode = 'en' | 'pt-BR' | 'de' | 'fr' | 'it' | 'zh-CN' | 'ja' | 'ko' | 'hi';
export type MessageKey = keyof Messages;
type PluralBase<K> = K extends `${infer B}_one` ? B : never;
export type PluralKey = PluralBase<MessageKey>;

/** Shown in the language picker, each in its own language. */
export const LANGUAGES: { code: LanguageCode; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'pt-BR', label: 'Português (Brasil)' },
  { code: 'de', label: 'Deutsch' },
  { code: 'fr', label: 'Français' },
  { code: 'it', label: 'Italiano' },
  { code: 'zh-CN', label: '中文（简体）' },
  { code: 'ja', label: '日本語' },
  { code: 'ko', label: '한국어' },
  { code: 'hi', label: 'हिन्दी' },
];

const DICTIONARIES: Record<LanguageCode, Messages> = {
  en,
  'pt-BR': ptBR,
  de,
  fr,
  it,
  'zh-CN': zhCN,
  ja,
  ko,
  hi,
};

const STORAGE_KEY = 'ibis_lang';

export function isLanguageCode(value: unknown): value is LanguageCode {
  return typeof value === 'string' && value in DICTIONARIES;
}

function initialLanguage(): LanguageCode {
  const stored = localStorage.getItem(STORAGE_KEY);
  return isLanguageCode(stored) ? stored : 'en';
}

type Params = Record<string, string | number>;

function interpolate(text: string, params?: Params): string {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (match, name) => (name in params ? String(params[name]) : match));
}

interface I18nContextType {
  lang: LanguageCode;
  setLang: (lang: string) => void;
  t: (key: MessageKey, params?: Params) => string;
  tn: (key: PluralKey, count: number, params?: Params) => string;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<LanguageCode>(() => {
    const initial = initialLanguage();
    setFormatLocale(initial);
    return initial;
  });

  const setLang = useCallback((next: string) => {
    if (!isLanguageCode(next)) return;
    localStorage.setItem(STORAGE_KEY, next);
    setFormatLocale(next);
    document.documentElement.lang = next;
    setLangState(next);
  }, []);

  const value = useMemo<I18nContextType>(() => {
    const dict = DICTIONARIES[lang];
    const t = (key: MessageKey, params?: Params) => interpolate(dict[key] ?? en[key] ?? key, params);
    const plural = new Intl.PluralRules(lang);
    const tn = (key: PluralKey, count: number, params?: Params) => {
      const form = plural.select(count) === 'one' ? 'one' : 'other';
      return t(`${key}_${form}` as MessageKey, { count, ...params });
    };
    return { lang, setLang, t, tn };
  }, [lang, setLang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) throw new Error('useI18n must be used within I18nProvider');
  return context;
}
