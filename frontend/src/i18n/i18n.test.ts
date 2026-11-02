import { de } from './locales/de';
import { en } from './locales/en';
import { fr } from './locales/fr';
import { hi } from './locales/hi';
import { it as italian } from './locales/it';
import { ja } from './locales/ja';
import { ko } from './locales/ko';
import { ptBR } from './locales/pt-BR';
import { zhCN } from './locales/zh-CN';
import type { PixKeyErrorCode } from '../utils/pixKey';

const LOCALES = { 'pt-BR': ptBR, de, fr, it: italian, 'zh-CN': zhCN, ja, ko, hi };

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe('translations', () => {
  for (const [code, dict] of Object.entries(LOCALES)) {
    it(`${code} keeps every {placeholder} of the English text`, () => {
      const problems = Object.entries(en)
        .filter(([key, text]) => {
          const translated = (dict as Record<string, string>)[key];
          // A plural "_one" form may say "1" in words instead of {count}; everything else must match exactly
          if (key.endsWith('_one')) {
            return placeholders(translated).some((p) => !placeholders(text).includes(p));
          }
          return placeholders(translated).join() !== placeholders(text).join();
        })
        .map(([key]) => key);
      expect(problems).toEqual([]);
    });

    it(`${code} has no empty texts`, () => {
      expect(Object.entries(dict).filter(([, text]) => !text.trim())).toEqual([]);
    });
  }

  it('every plural key has both forms', () => {
    const keys = Object.keys(en);
    const bases = keys.filter((k) => k.endsWith('_one')).map((k) => k.slice(0, -4));
    expect(bases.length).toBeGreaterThan(0);
    for (const base of bases) expect(keys).toContain(`${base}_other`);
  });

  it('every PIX key error code has a message', () => {
    const codes: PixKeyErrorCode[] = [
      'empty', 'badEmail', 'emailTooLong', 'notAKey', 'notBrazilianPhone', 'phoneDigits',
      'badAreaCode', 'mobileStartsWith9', 'badCpf', 'badCnpj', 'checkNumber', 'wrongLength',
    ];
    for (const code of codes) expect(Object.keys(en)).toContain(`pix.error.${code}`);
  });
});
