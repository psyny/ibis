import { buildPix, crc16 } from './pix';

describe('buildPix', () => {
  it('builds a valid copia-e-cola code with the amount', () => {
    const pix = buildPix('rafael@example.com', 'Rafaél Ção da Silva Júnior Neto', 5);
    expect(pix.kind).toBe('email');
    expect(pix.merchant.length).toBeLessThanOrEqual(25);
    expect(pix.merchant).toBe('Rafael Cao da Silva Junio');
    expect(pix.code).toContain('BR.GOV.BCB.PIX');
    expect(pix.code).toContain('0118rafael@example.com');
    expect(pix.code).toContain('54045.00'); // amount field
    expect(pix.code).toContain('5303986'); // BRL
    // Last 4 chars are the CRC of everything before them
    const body = pix.code.slice(0, -4);
    expect(body.endsWith('6304')).toBe(true);
    expect(pix.code.slice(-4)).toBe(crc16(body));
  });

  it('cleans up a formatted phone key before building', () => {
    const pix = buildPix('+55 (21) 99381-5159', 'Ana', 12.5);
    expect(pix.kind).toBe('phone');
    expect(pix.pixkey).toBe('+5521993815159');
    expect(pix.code).toContain('0114+5521993815159');
  });

  it('explains keys that cannot be used', () => {
    expect(() => buildPix('+55 21 993815-1593', 'Ana', 5)).toThrow(/10 digits after the area code/);
    expect(() => buildPix('hello world', 'Ana', 5)).toThrow(/not a PIX key/);
  });
});
