import { isValidCnpj, isValidCpf, parsePixKey } from './pixKey';

const VALID_CPF = '52998224725';
const VALID_CNPJ = '11222333000181';

function key(raw: string) {
  const result = parsePixKey(raw);
  if (!result.ok) throw new Error(`expected "${raw}" to be valid, got: ${result.error}`);
  return [result.kind, result.key];
}

function error(raw: string) {
  const result = parsePixKey(raw);
  if (result.ok) throw new Error(`expected "${raw}" to be invalid, got ${result.kind} ${result.key}`);
  return result.error;
}

describe('check digits', () => {
  it('validates CPF and CNPJ', () => {
    expect(isValidCpf(VALID_CPF)).toBe(true);
    expect(isValidCpf('52998224724')).toBe(false);
    expect(isValidCpf('11111111111')).toBe(false);
    expect(isValidCnpj(VALID_CNPJ)).toBe(true);
    expect(isValidCnpj('11222333000182')).toBe(false);
  });
});

describe('parsePixKey: phones in every common format', () => {
  it.each([
    '+55 21 99381-5159',
    '+55 (21) 99381-5159',
    '+5521993815159',
    '(21) 99381-5159',
    '21 99381-5159',
    '21993815159',
    '021 99381-5159',
    '5521993815159',
    '55 21 99381 5159',
    ' +55 21 99381‑5159 ', // non-breaking spaces from copy/paste
  ])('%s', (raw) => {
    expect(key(raw.replace('‑', '-'))).toEqual(['phone', '+5521993815159']);
  });

  it('accepts landlines (8 digits)', () => {
    expect(key('+55 21 3381-5159')).toEqual(['phone', '+552133815159']);
    expect(key('(21) 3381-5159')).toEqual(['phone', '+552133815159']);
  });

  it('explains wrong phone numbers precisely', () => {
    // The real-world typo: one digit too many
    expect(error('+55 21 993815-1593')).toMatch(/10 digits after the area code/);
    expect(error('55 21 993815-1593')).toMatch(/10 digits after the area code/);
    expect(error('+1 415 555 0100')).toMatch(/Only Brazilian/);
    expect(error('+55 21 8938-15159')).toMatch(/start with 9/);
    expect(error('+55 01 99381-5159')).toMatch(/area code/);
  });
});

describe('parsePixKey: documents, emails and random keys', () => {
  it('CPF with or without formatting', () => {
    expect(key('529.982.247-25')).toEqual(['cpf', VALID_CPF]);
    expect(key(VALID_CPF)).toEqual(['cpf', VALID_CPF]);
    expect(error('529.982.247-24')).toMatch(/CPF.*check digits/);
  });

  it('CNPJ with or without formatting', () => {
    expect(key('11.222.333/0001-81')).toEqual(['cnpj', VALID_CNPJ]);
    expect(key(VALID_CNPJ)).toEqual(['cnpj', VALID_CNPJ]);
    expect(error('11.222.333/0001-82')).toMatch(/CNPJ.*check digits/);
  });

  it('emails', () => {
    expect(key('  Rafael.Silva@Example.COM ')).toEqual(['email', 'rafael.silva@example.com']);
    expect(key('mailto:ana@x.com')).toEqual(['email', 'ana@x.com']);
    expect(error('ana@')).toMatch(/email/);
  });

  it('random keys, with or without dashes', () => {
    const uuid = '123e4567-e89b-12d3-a456-426614174000';
    expect(key(uuid.toUpperCase())).toEqual(['random', uuid]);
    expect(key(uuid.replace(/-/g, ''))).toEqual(['random', uuid]);
  });

  it('rejects things that are not keys', () => {
    expect(error('')).toMatch(/Enter a PIX key/);
    expect(error('hello world')).toMatch(/not a PIX key/);
    expect(error('12345')).toMatch(/5 digits/);
  });
});
