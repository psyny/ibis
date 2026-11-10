import http from 'node:http';
import { createHandler } from './app.js';
import { SessionManager } from './sessions.js';

const PORT = Number(process.env.PORT || 3001);
const TOKEN = process.env.WHATSAPP_SERVICE_TOKEN || '';
const DATA_DIR = process.env.DATA_DIR || './data/sessions';

if (TOKEN.length < 16) {
  console.error('WHATSAPP_SERVICE_TOKEN must be set (at least 16 characters).');
  process.exit(1);
}

const manager = new SessionManager(DATA_DIR);
const server = http.createServer(createHandler({ manager, token: TOKEN }));

// "::" also accepts IPv4, and is needed for Railway's private network (IPv6)
server.listen(PORT, '::', () => {
  console.log(`Ibis WhatsApp service on port ${PORT}, sessions in ${DATA_DIR}`);
  manager.restoreAll().catch((err) => console.error('Restoring sessions failed:', err));
});

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
