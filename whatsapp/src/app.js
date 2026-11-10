// HTTP API used by the Ibis backend (never by browsers). Every route except /health needs
// "Authorization: Bearer <WHATSAPP_SERVICE_TOKEN>".
//
//   GET  /health
//   GET  /sessions/:id              -> { status, qr, phone, name, error }
//   POST /sessions/:id/connect      -> starts it; poll GET for the QR code
//   POST /sessions/:id/logout       -> unlinks the number and deletes its login data
//   GET  /sessions/:id/groups       -> [{ id, name, participants }]
//   POST /sessions/:id/messages     { to, text } -> { id }   (to: group jid or phone digits)
import { HttpError, isAuthorized, readJson, sendJson } from './http.js';

const ROUTE = /^\/sessions\/([^/]+)(?:\/(connect|logout|groups|messages))?\/?$/;
const MAX_TEXT = 4096;

export function createHandler({ manager, token }) {
  return async (req, res) => {
    try {
      const url = new URL(req.url, 'http://localhost');
      if (url.pathname === '/health') return sendJson(res, 200, { ok: true });
      if (!isAuthorized(req, token)) throw new HttpError(401, 'Unauthorized');

      const match = url.pathname.match(ROUTE);
      if (!match) throw new HttpError(404, 'Not found');
      const [, id, action] = match;
      const session = manager.session(id);
      const route = `${req.method} ${action || ''}`;

      switch (route) {
        case 'GET ':
          return sendJson(res, 200, session.info());
        case 'POST connect':
          await session.start();
          return sendJson(res, 200, session.info());
        case 'POST logout':
          await session.logout();
          return sendJson(res, 200, session.info());
        case 'GET groups':
          return sendJson(res, 200, await session.groups());
        case 'POST messages': {
          const { to, text } = await readJson(req);
          if (typeof to !== 'string' || !to) throw new HttpError(400, '"to" is required');
          if (typeof text !== 'string' || !text.trim()) throw new HttpError(400, '"text" is required');
          if (text.length > MAX_TEXT) throw new HttpError(400, `"text" is longer than ${MAX_TEXT} characters`);
          return sendJson(res, 200, await session.send(to, text));
        }
        default:
          throw new HttpError(405, 'Method not allowed');
      }
    } catch (err) {
      const status = err instanceof HttpError ? err.status : 500;
      if (status === 500) console.error(err);
      return sendJson(res, status, { error: err.message || 'Internal error' });
    }
  };
}
