import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
const root = process.cwd();
const port = Number(process.argv[2] || process.env.PORT || 3000);
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.json': 'application/json', '.md': 'text/plain' };
http.createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    let file = path.resolve(root, `.${pathname}`);
    if (file !== root && !file.startsWith(root + path.sep)) { response.writeHead(403).end(); return; }
    if (pathname.split('/').some(part => part.startsWith('.'))) { response.writeHead(403).end(); return; }
    try { if (!(await stat(file)).isFile()) file = path.join(root, 'index.html'); }
    catch { if (path.extname(pathname)) { response.writeHead(404).end('Not found'); return; } file = path.join(root, 'index.html'); }
    const data = await readFile(file);
    response.writeHead(200, { 'Content-Type': `${types[path.extname(file)] || 'application/octet-stream'}; charset=utf-8`, 'Cache-Control': 'no-store' });
    response.end(data);
  } catch { response.writeHead(400).end('Invalid request'); }
}).listen(port, '127.0.0.1', () => console.log(`IU Study Assistant: http://localhost:${port}`));
