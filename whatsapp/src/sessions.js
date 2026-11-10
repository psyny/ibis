// One WhatsApp Web session per household (session id = household id), using Baileys.
// Login data lives in DATA_DIR/<id>/ (keep it on a persistent volume, or the QR has to be scanned again).
import fs from 'node:fs/promises';
import path from 'node:path';
import makeWASocket, {
  Browsers,
  DisconnectReason,
  fetchLatestBaileysVersion,
  jidNormalizedUser,
  useMultiFileAuthState,
} from '@whiskeysockets/baileys';
import pino from 'pino';
import QRCode from 'qrcode';
import { HttpError } from './http.js';

const logger = pino({ level: process.env.BAILEYS_LOG_LEVEL || 'warn' });
const MAX_RETRY_DELAY_MS = 60_000;

/** A session id must be safe as a folder name (household ids are UUIDs). */
export function validSessionId(id) {
  return /^[A-Za-z0-9-]{1,64}$/.test(id);
}

/** Digits of a phone number with country code, or null. */
export function phoneDigits(value) {
  const digits = String(value || '').replace(/\D/g, '');
  return digits.length >= 8 && digits.length <= 15 ? digits : null;
}

class Session {
  constructor(id, dir) {
    this.id = id;
    this.dir = dir;
    this.sock = null;
    this.status = 'disconnected'; // disconnected | connecting | qr | connected
    this.qr = null; // data URL while waiting for the scan
    this.phone = null;
    this.name = null;
    this.error = null;
    this.retries = 0;
    this.stopped = false; // set by logout: don't reconnect
  }

  info() {
    return { status: this.status, qr: this.qr, phone: this.phone, name: this.name, error: this.error };
  }

  async start() {
    if (this.sock || this.status === 'connecting') return;
    this.stopped = false;
    this.status = 'connecting';
    this.error = null;
    try {
      await this.open();
    } catch (err) {
      this.status = 'disconnected';
      this.error = `Could not start WhatsApp: ${err.message}`;
      logger.error({ err, session: this.id }, 'session start failed');
    }
  }

  async open() {
    await fs.mkdir(this.dir, { recursive: true });
    const { state, saveCreds } = await useMultiFileAuthState(this.dir);
    // Use the WhatsApp Web version WhatsApp currently expects; fall back to Baileys' built-in one offline
    const { version } = await fetchLatestBaileysVersion().catch(() => ({ version: undefined }));
    const sock = makeWASocket({
      auth: state,
      version,
      logger,
      browser: Browsers.ubuntu('Ibis'),
      markOnlineOnConnect: false, // don't stop the phone from getting notifications
      syncFullHistory: false,
    });
    this.sock = sock;
    sock.ev.on('creds.update', saveCreds);
    sock.ev.on('connection.update', (update) => this.onUpdate(sock, state, update));
  }

  async onUpdate(sock, state, { connection, lastDisconnect, qr }) {
    if (sock !== this.sock) return; // an older socket
    if (qr) {
      this.status = 'qr';
      this.qr = await QRCode.toDataURL(qr, { margin: 1, width: 320 });
    }
    if (connection === 'open') {
      this.status = 'connected';
      this.qr = null;
      this.error = null;
      this.retries = 0;
      this.phone = sock.user?.id ? jidNormalizedUser(sock.user.id).split('@')[0] : null;
      this.name = sock.user?.name || sock.user?.verifiedName || null;
      logger.info({ session: this.id, phone: this.phone }, 'connected');
    }
    if (connection !== 'close') return;

    this.sock = null;
    this.qr = null;
    const code = lastDisconnect?.error?.output?.statusCode;
    if (code === DisconnectReason.loggedOut) {
      // Unlinked from the phone (or by logout): forget the login data
      await this.forget();
      if (!this.stopped) this.error = 'The number was unlinked from WhatsApp. Connect again.';
      return;
    }
    const linked = Boolean(state.creds?.me);
    if (this.stopped || (!linked && code !== DisconnectReason.restartRequired)) {
      // e.g. the QR code was never scanned: wait for the manager to press Connect again
      this.status = 'disconnected';
      if (!linked && !this.stopped) this.error = 'The QR code expired. Connect again.';
      return;
    }
    // Lost connection (or the normal restart right after scanning): reconnect with backoff
    this.status = 'connecting';
    const delay = code === DisconnectReason.restartRequired ? 0 : Math.min(MAX_RETRY_DELAY_MS, 1000 * 2 ** this.retries++);
    logger.warn({ session: this.id, code, delay }, 'connection closed, reconnecting');
    setTimeout(() => {
      this.status = 'disconnected';
      this.start();
    }, delay);
  }

  async logout() {
    this.stopped = true;
    const sock = this.sock;
    if (sock) {
      try {
        await sock.logout();
      } catch (err) {
        logger.warn({ err, session: this.id }, 'logout failed; forgetting the session anyway');
      }
    }
    this.sock = null;
    await this.forget();
  }

  async forget() {
    await fs.rm(this.dir, { recursive: true, force: true });
    this.status = 'disconnected';
    this.qr = null;
    this.phone = null;
    this.name = null;
  }

  requireConnected() {
    if (this.status !== 'connected' || !this.sock) {
      throw new HttpError(409, 'WhatsApp is not connected for this household');
    }
    return this.sock;
  }

  async groups() {
    const sock = this.requireConnected();
    const all = await sock.groupFetchAllParticipating();
    return Object.values(all).map((g) => ({ id: g.id, name: g.subject || '', participants: g.participants?.length || 0 }));
  }

  /** `to`: a group jid ("...@g.us") or a phone number with country code. */
  async send(to, text) {
    const sock = this.requireConnected();
    let jid;
    if (String(to).endsWith('@g.us')) {
      jid = to;
    } else {
      const digits = phoneDigits(to);
      if (!digits) throw new HttpError(400, `"${to}" is not a phone number`);
      // Also finds the right id for Brazilian numbers with or without the extra 9
      const [found] = await sock.onWhatsApp(digits);
      if (!found?.exists) throw new HttpError(400, `${digits} is not on WhatsApp`);
      jid = found.jid;
    }
    const message = await sock.sendMessage(jid, { text });
    return { id: message?.key?.id || null };
  }
}

export class SessionManager {
  constructor(dataDir) {
    this.dataDir = dataDir;
    this.sessions = new Map();
  }

  session(id) {
    if (!validSessionId(id)) throw new HttpError(400, 'Invalid session id');
    let session = this.sessions.get(id);
    if (!session) {
      session = new Session(id, path.join(this.dataDir, id));
      this.sessions.set(id, session);
    }
    return session;
  }

  /** At startup: reconnect every session that has saved login data. */
  async restoreAll() {
    await fs.mkdir(this.dataDir, { recursive: true });
    const entries = await fs.readdir(this.dataDir, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory() || !validSessionId(entry.name)) continue;
      const hasCreds = await fs
        .access(path.join(this.dataDir, entry.name, 'creds.json'))
        .then(() => true)
        .catch(() => false);
      if (hasCreds) await this.session(entry.name).start();
    }
  }
}
