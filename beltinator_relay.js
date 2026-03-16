/**
 * beltinator_relay.js — WebSocket Relay Server
 * Bridges Surface tablet controller UI to the IGLOO panoramic renderer.
 *
 * ARCHITECTURE:
 *   [Surface Tablet]  <--WSS-->  [This Relay]  <--WSS-->  [IGLOO Renderer]
 *   ?mode=controller                                       ?mode=igloo
 *
 * SETUP:
 *   1. npm install ws express
 *   2. Generate SSL certs:
 *      openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes
 *   3. Place beltinator_vr.html (or index.html) in the same directory
 *   4. node beltinator_relay.js
 *
 * URLs:
 *   IGLOO renderer:    https://<host>:8443/?mode=igloo
 *   Tablet controller: https://<host>:8443/?mode=controller
 *   Standalone:        https://<host>:8443/
 *
 * PROTOCOL (Controller -> IGLOO):
 *   { type:'state',    data:{ lstar, energy, alpha, kp, dst, vsw, ... } }
 *   { type:'preset',   data:'quiet'|'moderate'|'intense'|'recovery' }
 *   { type:'camera',   data:{ camH, camV, camDist } }
 *   { type:'focusSat', data:'RBSP'|'THEMIS-A'|'GOES'|'LEO'|'Lomonosov' }
 *   { type:'zoomBack' }
 *
 * PROTOCOL (IGLOO -> Controller):
 *   { type:'computed', data:{ bounce, psd, flux, dll, kp, lmp, ... } }
 *   { type:'status',   data:'igloo_connected'|'controller_connected' }
 */

const express = require('express');
const http = require('http');
const https = require('https');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8443;

const app = express();
app.use(express.static(path.join(__dirname)));
app.get('/', (req, res) => {
  const indexPath = path.join(__dirname, 'index.html');
  const beltPath = path.join(__dirname, 'beltinator_vr.html');
  if (fs.existsSync(indexPath)) res.sendFile(indexPath);
  else if (fs.existsSync(beltPath)) res.sendFile(beltPath);
  else res.status(404).send('beltinator_vr.html or index.html not found');
});

let server;
const keyPath = path.join(__dirname, 'key.pem');
const certPath = path.join(__dirname, 'cert.pem');
if (fs.existsSync(keyPath) && fs.existsSync(certPath)) {
  server = https.createServer({ key: fs.readFileSync(keyPath), cert: fs.readFileSync(certPath) }, app);
  console.log('HTTPS enabled');
} else {
  server = http.createServer(app);
  console.warn('No SSL certs. Running HTTP. Generate: openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes');
}

const wss = new WebSocket.Server({ server });
const clients = { igloo: new Set(), controller: new Set() };

function broadcast(set, msg) {
  const d = typeof msg === 'string' ? msg : JSON.stringify(msg);
  set.forEach(c => { if (c.readyState === WebSocket.OPEN) c.send(d); });
}

wss.on('connection', (ws, req) => {
  const url = new URL(req.url, `https://${req.headers.host}`);
  const mode = url.searchParams.get('mode');
  if (!mode || !clients[mode]) { ws.close(); return; }

  clients[mode].add(ws);
  console.log(`${mode} connected (${clients[mode].size})`);
  const other = mode === 'controller' ? 'igloo' : 'controller';
  broadcast(clients[other], { type: 'status', data: `${mode}_connected` });

  ws.on('message', data => {
    try {
      broadcast(clients[other], JSON.parse(data));
    } catch(e) { console.error('Parse error:', e.message); }
  });

  ws.on('close', () => {
    clients[mode].delete(ws);
    console.log(`${mode} disconnected (${clients[mode].size})`);
    broadcast(clients[other], { type: 'status', data: `${mode}_disconnected` });
  });

  ws.on('error', err => console.error(`WS error (${mode}):`, err.message));
});

app.get('/status', (req, res) => res.json({
  igloo: clients.igloo.size, controller: clients.controller.size, uptime: Math.floor(process.uptime())
}));

server.listen(PORT, '0.0.0.0', () => {
  const p = fs.existsSync(keyPath) ? 'https' : 'http';
  console.log(`\nBELTINATOR RELAY on port ${PORT}`);
  console.log(`  IGLOO:      ${p}://localhost:${PORT}/?mode=igloo`);
  console.log(`  Controller: ${p}://localhost:${PORT}/?mode=controller`);
  console.log(`  Standalone: ${p}://localhost:${PORT}/`);
  console.log(`  Status:     ${p}://localhost:${PORT}/status\n`);
});
