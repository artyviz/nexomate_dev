const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const pino = require('pino');
const QRCode = require('qrcode');
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8001;
const PYTHON_BACKEND = 'http://localhost:8000/api/whatsapp/inbound_json';
const AUTH_DIR = path.join(__dirname, 'auth_info');

let currentQR = null;
let currentQRDataUrl = null;
let isConnected = false;
let connectedPhone = null;
let sock = null;

// Track recently processed message IDs to prevent duplicate processing
const processedMsgIds = new Set();
// Track replies sent by this bot to avoid responding to our own outbound messages
const botSentTexts = new Set();

function extractText(message) {
    if (!message) return '';
    if (message.ephemeralMessage?.message) message = message.ephemeralMessage.message;
    if (message.viewOnceMessage?.message) message = message.viewOnceMessage.message;
    if (message.viewOnceMessageV2?.message) message = message.viewOnceMessageV2.message;
    if (message.documentWithCaptionMessage?.message) message = message.documentWithCaptionMessage.message;

    return message.conversation ||
           message.extendedTextMessage?.text ||
           message.imageMessage?.caption ||
           message.videoMessage?.caption ||
           message.buttonsResponseMessage?.selectedDisplayText ||
           message.templateButtonReplyMessage?.selectedId ||
           message.listResponseMessage?.title ||
           '';
}

async function startSock() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

    sock = makeWASocket({
        auth: state,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: false,
        browser: ['Nexomate Lead AI', 'Chrome', '120.0.0']
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            currentQR = qr;
            try {
                currentQRDataUrl = await QRCode.toDataURL(qr, { margin: 2, scale: 7 });
            } catch (err) {
                console.error('Error generating QR data URL:', err);
            }
            isConnected = false;
            console.log('[WhatsApp Bridge] New QR Code generated. Scan to link device.');
        }

        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log('[WhatsApp Bridge] Connection closed. Reconnecting:', shouldReconnect);
            isConnected = false;
            connectedPhone = null;
            if (shouldReconnect) {
                setTimeout(startSock, 3000);
            } else {
                console.log('[WhatsApp Bridge] Logged out. Clearing credentials...');
                if (fs.existsSync(AUTH_DIR)) {
                    fs.rmSync(AUTH_DIR, { recursive: true, force: true });
                }
                setTimeout(startSock, 2000);
            }
        } else if (connection === 'open') {
            isConnected = true;
            currentQR = null;
            currentQRDataUrl = null;
            const jid = sock.user?.id || '';
            connectedPhone = jid.split(':')[0] || jid.split('@')[0];
            console.log(`[WhatsApp Bridge] WhatsApp Connected successfully as +${connectedPhone}`);
        }
    });

    sock.ev.on('messages.upsert', async (upsert) => {
        const { messages, type } = upsert;
        console.log(`[WhatsApp Event] messages.upsert received, type=${type}, count=${messages?.length || 0}`);

        for (const msg of messages || []) {
            const msgId = msg.key?.id;
            if (!msgId || processedMsgIds.has(msgId)) continue;
            processedMsgIds.add(msgId);
            // Cap cache size
            if (processedMsgIds.size > 2000) {
                const first = processedMsgIds.values().next().value;
                processedMsgIds.delete(first);
            }

            const remoteJid = msg.key?.remoteJid;
            if (!remoteJid) continue;

            // Ignore status broadcast / stories
            if (remoteJid === 'status@broadcast') continue;
            // Ignore group chats
            if (remoteJid.endsWith('@g.us')) continue;

            const text = extractText(msg.message).trim();
            if (!text) continue;

            // Prevent responding to bot's own outbound messages
            if (botSentTexts.has(text)) {
                botSentTexts.delete(text);
                continue;
            }

            // If fromMe is true: only process if the user is explicitly testing by sending a message to themselves
            const isSelfTest = remoteJid.includes(connectedPhone || '____');
            if (msg.key.fromMe && !isSelfTest) {
                console.log(`[WhatsApp] Ignoring outgoing message sent by account owner to ${remoteJid}`);
                continue;
            }

            const name = msg.pushName || 'WhatsApp Contact';
            // Extract numeric phone number from JID
            const rawPhone = remoteJid.split('@')[0].split(':')[0];
            const phone = rawPhone.startsWith('+') ? rawPhone : ('+' + rawPhone);

            console.log(`[WhatsApp Inbound ⚡] From: ${name} (${phone}) [JID: ${remoteJid}] - "${text}"`);

            // Forward to Python AI lead engine
            try {
                const response = await fetch(PYTHON_BACKEND, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone, name, text })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data && data.reply) {
                        const replyText = data.reply;
                        console.log(`[WhatsApp Outbound 🚀] Replying to ${remoteJid}: "${replyText.slice(0, 60)}..."`);
                        botSentTexts.add(replyText);
                        // Instant dispatch
                        await sock.sendMessage(remoteJid, { text: replyText });
                    }
                } else {
                    const errText = await response.text();
                    console.error('[WhatsApp Bridge] Backend returned HTTP', response.status, errText);
                }
            } catch (err) {
                console.error('[WhatsApp Bridge] Failed to forward message to Python backend:', err.message);
            }
        }
    });

    // ── Missed Call Intercept Listener ───────────────────────────────────────
    sock.ev.on('call', async (callEvents) => {
        for (const call of callEvents || []) {
            console.log(`[WhatsApp Call Event] From: ${call.from}, Status: ${call.status}, isVideo: ${call.isVideo}`);
            // Intercept missed calls (timeout = rang and missed, reject = declined/busy)
            if (call.status === 'timeout' || call.status === 'reject') {
                const raw = call.from.split('@')[0].split(':')[0];
                const phone = raw.startsWith('+') ? raw : ('+' + raw);
                console.log(`[Missed Call Intercepted 📞] From ${phone}. Dispatching recovery flow...`);

                try {
                    await fetch('http://localhost:8000/api/whatsapp/missed_call', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            phone: phone,
                            name: 'Caller',
                            source: 'WhatsApp Missed Call'
                        })
                    });
                } catch (err) {
                    console.error('[Missed Call Error] Failed to inform backend:', err.message);
                }
            }
        }
    });
}

// ── HTTP API Server for Streamlit Dashboard ────────────────────────────────
const server = http.createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }

    const url = new URL(req.url, `http://${req.headers.host}`);

    if (url.pathname === '/status' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            connected: isConnected,
            phone: connectedPhone ? `+${connectedPhone}` : null,
            qr: currentQRDataUrl
        }));
        return;
    }

    if (url.pathname === '/send' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', async () => {
            try {
                const data = JSON.parse(body || '{}');
                const to = data.to;
                const text = data.text;
                if (!to || !text) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Missing to or text' }));
                    return;
                }
                if (!sock || !isConnected) {
                    res.writeHead(503, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'WhatsApp not connected' }));
                    return;
                }
                const cleanPhone = to.replace(/\D/g, '');
                const jid = `${cleanPhone}@s.whatsapp.net`;
                botSentTexts.add(text);
                await sock.sendMessage(jid, { text });
                console.log(`[Outbound Dispatch 🚀] Sent message to ${jid}: "${text.slice(0, 50)}..."`);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true, to: jid }));
            } catch (err) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message }));
            }
        });
        return;
    }

    if (url.pathname === '/logout' && req.method === 'POST') {
        try {
            if (sock) {
                await sock.logout();
            }
            if (fs.existsSync(AUTH_DIR)) {
                fs.rmSync(AUTH_DIR, { recursive: true, force: true });
            }
            isConnected = false;
            connectedPhone = null;
            setTimeout(startSock, 1000);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true, message: 'Logged out. Generating new QR code...' }));
        } catch (err) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: err.message }));
        }
        return;
    }

    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(PORT, () => {
    console.log(`[WhatsApp Bridge API] Listening on http://localhost:${PORT}`);
    startSock();
});
