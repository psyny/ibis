/**
 * Understand whatever people type as a PIX key and turn it into the canonical form
 * PIX expects, or explain exactly what is wrong.
 *
 * Canonical forms: email (lower case), CPF (11 digits), CNPJ (14 digits),
 * phone (+55 + area code + number), random key (lower-case UUID 8-4-4-4-12).
 *
 * Problems come back as a `code` + `params` so the screen can show them in the
 * household's language (keys "pix.error.<code>"); `error` is the English text.
 */

export type PixKeyKind = 'email' | 'cpf' | 'cnpj' | 'phone' | 'random';

export type PixKeyErrorCode =
  | 'empty'
  | 'badEmail'
  | 'emailTooLong'
  | 'notAKey'
  | 'notBrazilianPhone'
  | 'phoneDigits'
  | 'badAreaCode'
  | 'mobileStartsWith9'
  | 'badCpf'
  | 'badCnpj'
  | 'checkNumber'
  | 'wrongLength';

export type PixKeyParams = Record<string, string | number>;

export type PixKeyResult =
  | { ok: true; kind: PixKeyKind; key: string }
  | { ok: false; code: PixKeyErrorCode; params: PixKeyParams; error: string };

/** English messages (the translated ones live in i18n/locales as "pix.error.<code>"). */
const ENGLISH: Record<PixKeyErrorCode, (p: PixKeyParams) => string> = {
  empty: () => 'Enter a PIX key.',
  badEmail: (p) => `“${p.text}” doesn't look like a valid email.`,
  emailTooLong: () => 'Email keys can have at most 77 characters.',
  notAKey: (p) => `“${p.text}” is not a PIX key. Use an email, CPF, CNPJ, phone number or random key.`,
  notBrazilianPhone: () => 'Only Brazilian phone numbers (+55) can be PIX keys.',
  phoneDigits: (p) =>
    `This looks like a phone number, but it has ${p.count} digit${p.count === 1 ? '' : 's'} after the area code. Brazilian numbers have 9 (mobile) or 8 (landline), e.g. +55 21 99381-5159.`,
  badAreaCode: (p) => `“${p.code}” is not a valid area code (DDD).`,
  mobileStartsWith9: () => 'Mobile numbers with 9 digits start with 9 (e.g. 99381-5159).',
  badCpf: () => 'This looks like a CPF, but its check digits are wrong. Please check the number.',
  badCnpj: () => 'This looks like a CNPJ, but its check digits are wrong. Please check the number.',
  checkNumber: () => 'Please check the number.',
  wrongLength: (p) =>
    `“${p.text}” has ${p.count} digits: that is not a CPF (11), CNPJ (14) or phone number (area code + 8 or 9 digits).`,
};

type Problem = { code: PixKeyErrorCode; params: PixKeyParams };

const ok = (kind: PixKeyKind, key: string): PixKeyResult => ({ ok: true, kind, key });
const fail = (code: PixKeyErrorCode, params: PixKeyParams = {}): PixKeyResult => ({
  ok: false,
  code,
  params,
  error: ENGLISH[code](params),
});
const failWith = (problem: Problem): PixKeyResult => fail(problem.code, problem.params);

export function isValidCpf(digits: string): boolean {
  if (!/^\d{11}$/.test(digits) || /^(\d)\1{10}$/.test(digits)) return false;
  const check = (length: number) => {
    let sum = 0;
    for (let i = 0; i < length; i++) sum += Number(digits[i]) * (length + 1 - i);
    const rest = (sum * 10) % 11;
    return rest === 10 ? 0 : rest;
  };
  return check(9) === Number(digits[9]) && check(10) === Number(digits[10]);
}

export function isValidCnpj(digits: string): boolean {
  if (!/^\d{14}$/.test(digits) || /^(\d)\1{13}$/.test(digits)) return false;
  const check = (length: number) => {
    const weights = length === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const sum = weights.reduce((acc, w, i) => acc + w * Number(digits[i]), 0);
    const rest = sum % 11;
    return rest < 2 ? 0 : 11 - rest;
  };
  return check(12) === Number(digits[12]) && check(13) === Number(digits[13]);
}

/**
 * Checks a Brazilian number without the country code: area code (2 digits, 11-99)
 * plus an 8-digit landline or a 9-digit mobile starting with 9.
 */
function checkNationalPhone(national: string): Problem | null {
  if (national.length < 10 || national.length > 11) {
    return { code: 'phoneDigits', params: { count: national.length - 2 } };
  }
  if (!/^[1-9][1-9]/.test(national)) return { code: 'badAreaCode', params: { code: national.slice(0, 2) } };
  if (national.length === 11 && national[2] !== '9') return { code: 'mobileStartsWith9', params: {} };
  return null;
}

export function parsePixKey(raw: string): PixKeyResult {
  // Drop invisible characters (copy-pasting from apps often brings them) and outer spaces
  const text = raw.replace(/[​-‍﻿ ]/g, ' ').trim();
  if (!text) return fail('empty');

  // Email
  if (text.includes('@')) {
    const email = text.replace(/\s+/g, '').replace(/^mailto:/i, '').toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return fail('badEmail', { text });
    if (email.length > 77) return fail('emailTooLong');
    return ok('email', email);
  }

  // Random key (EVP): a UUID, 32 hex characters with or without dashes
  const hex = text.replace(/[\s-]/g, '');
  if (/^[0-9a-f]{32}$/i.test(hex) && /[a-f]/i.test(hex)) {
    const h = hex.toLowerCase();
    return ok('random', `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`);
  }

  // Everything else must be numbers with common separators
  if (!/^\+?[\d\s.\-/()]+$/.test(text)) return fail('notAKey', { text });
  const hasPlus = text.startsWith('+');
  const looksLikePhone = hasPlus || /[()]/.test(text);
  const looksLikeDocument = /[./]/.test(text);
  let digits = text.replace(/\D/g, '');

  if (hasPlus) {
    if (!digits.startsWith('55')) return fail('notBrazilianPhone');
    const problem = checkNationalPhone(digits.slice(2));
    return problem ? failWith(problem) : ok('phone', `+${digits}`);
  }

  if (digits.length === 14) {
    if (isValidCnpj(digits)) return ok('cnpj', digits);
    if (digits.startsWith('55') && !looksLikeDocument) {
      const problem = checkNationalPhone(digits.slice(2));
      return problem ? failWith(problem) : fail('checkNumber');
    }
    return fail('badCnpj');
  }

  if (digits.length === 11 && !looksLikePhone) {
    if (isValidCpf(digits)) return ok('cpf', digits);
    if (looksLikeDocument || checkNationalPhone(digits) !== null) return fail('badCpf');
    return ok('phone', `+55${digits}`); // e.g. "21993815159": a mobile number without +55
  }

  // Phone without the country code: optional trunk "0", area code, number
  if (digits.length === 12 && digits.startsWith('0')) digits = digits.slice(1);
  if (digits.length === 11 && digits.startsWith('0')) digits = digits.slice(1);
  if ((digits.length === 12 || digits.length === 13) && digits.startsWith('55')) {
    const problem = checkNationalPhone(digits.slice(2));
    return problem ? failWith(problem) : ok('phone', `+${digits}`);
  }
  if (looksLikePhone || digits.length === 10 || digits.length === 11) {
    const problem = checkNationalPhone(digits);
    return problem ? failWith(problem) : ok('phone', `+55${digits}`);
  }

  return fail('wrongLength', { text, count: digits.length });
}
