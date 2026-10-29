import { payload } from 'react-qrcode-pix';
import { parsePixKey, PixKeyKind } from './pixKey';

/** City is required by the PIX QR format; banks don't check it for person-to-person transfers. */
export const PIX_CITY = 'BRASIL';
const MAX_NAME = 25; // PIX limit for the receiver name
const MAX_CITY = 15; // PIX limit for the city

function plainName(name: string, max: number): string {
  return name
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-zA-Z\s]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, max)
    .trim();
}

export interface PixData {
  pixkey: string;
  merchant: string;
  city: string;
  amount: number | null;
}

/**
 * Build the PIX data and "copia e cola" code to pay `amount` to `name`.
 * The key is cleaned up and its type detected first (see pixKey.ts).
 * Throws an Error with a readable message if the key can't be used.
 */
export function buildPix(rawKey: string, name: string, amount: number | null): PixData & { code: string; kind: PixKeyKind } {
  const parsed = parsePixKey(rawKey);
  if (!parsed.ok) throw new Error(parsed.error);
  const data: PixData = {
    pixkey: parsed.key,
    merchant: plainName(name, MAX_NAME) || 'RECEBEDOR',
    city: plainName(PIX_CITY, MAX_CITY),
    amount: amount && amount > 0 ? Math.round(amount * 100) / 100 : null,
  };
  try {
    return { ...data, kind: parsed.kind, code: payload(data) };
  } catch (e) {
    throw new Error(`Could not create the PIX code: ${(e as Error).message}`);
  }
}

/** CRC16-CCITT (0xFFFF) as used by the PIX/EMV QR format. Exported for tests. */
export function crc16(text: string): string {
  let crc = 0xffff;
  for (let i = 0; i < text.length; i++) {
    crc ^= text.charCodeAt(i) << 8;
    for (let bit = 0; bit < 8; bit++) {
      crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xffff : (crc << 1) & 0xffff;
    }
  }
  return crc.toString(16).toUpperCase().padStart(4, '0');
}
