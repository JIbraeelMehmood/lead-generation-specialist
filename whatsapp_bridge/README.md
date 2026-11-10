# LeadFinder WhatsApp Bridge

This folder contains the Node.js Baileys bridge that enables real WhatsApp sending.

## Setup (one-time)

```bash
cd whatsapp_bridge
npm install
node server.js
```

Then scan the QR code that appears in the terminal with **WhatsApp → Settings → Linked Devices → Link a Device**.

After scanning, the bridge is connected. LeadFinder picks it up automatically.

## Important

- Use a **dedicated business number** — never your personal WhatsApp account.
- Session is saved in `.wa-auth/` — survives restarts.
- Messages must be approved in LeadFinder's WhatsApp tab before sending (unless auto-approve is enabled).

## Rate limits (default)

- 10 messages / hour
- 80 messages / day
- Quiet hours: 22:00–08:00 (configurable)
