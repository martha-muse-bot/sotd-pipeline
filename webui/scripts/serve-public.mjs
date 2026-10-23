#!/usr/bin/env node
/**
 * Local dev server for the public analytics site.
 *
 * Serves dist-public/ (build it first: `npm run build:public`, ~2s) with
 * SPA fallback, and proxies /api to a local backend (default :8000 — the
 * admin API, which is a superset of the public one) so pages render with
 * real data. One command after edits:
 *
 *   npm run dev:public
 *
 * Config via env: PORT (default 3200), API_TARGET (default http://127.0.0.1:8000).
 */
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DIST = path.resolve(__dirname, '..', 'dist-public');
const PORT = Number(process.env.PORT) || 3200;
const API_TARGET = process.env.API_TARGET || 'http://127.0.0.1:8000';
const API_HOST = API_TARGET.replace(/^https?:\/\//, '');

const CONTENT_TYPES = {
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.html': 'text/html; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
  '.ico': 'image/x-icon',
  '.png': 'image/png',
};

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) {
    const proxyReq = http.request(
      `${API_TARGET}${req.url}`,
      { method: req.method, headers: { host: API_HOST } },
      proxied => {
        res.writeHead(proxied.statusCode, proxied.headers);
        proxied.pipe(res);
      }
    );
    proxyReq.on('error', () => {
      res.writeHead(502, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ detail: `API proxy target unreachable: ${API_TARGET}` }));
    });
    req.pipe(proxyReq);
    return;
  }

  const routePath = decodeURIComponent(req.url.split('?')[0]);
  let file = path.join(DIST, routePath === '/' ? 'index.html' : routePath.slice(1));
  // SPA fallback: unknown paths get the app shell so react-router can route
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    file = path.join(DIST, 'index.html');
  }
  res.writeHead(200, { 'content-type': CONTENT_TYPES[path.extname(file)] || 'application/octet-stream' });
  res.end(fs.readFileSync(file));
});

server.listen(PORT, () => {
  console.log(`public site: http://localhost:${PORT}  (dist-public + /api -> ${API_TARGET})`);
});
