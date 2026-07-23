# ⚡ Lightning Control Center (LCC)

A beautiful, self-hosted Lightning node manager. Built for Bitcoin node runners.

**Live demo:** https://lcc.satslist.shop/dashboard

---

## Install Options

### Option 1 — One-command installer (bare metal Ubuntu/Debian)
```bash
curl -sSL https://raw.githubusercontent.com/lioranecho-cpu/lightning-control-center/main/install.sh | bash
```

### Option 2 — Docker
```bash
git clone https://github.com/lioranecho-cpu/lightning-control-center.git
cd lightning-control-center
docker compose up -d
```

### Option 3 — Docker (mock mode for testing)
```bash
docker run -e LCC_MOCK=true -p 8765:8765 lcc:latest
```

---

## Tiers

| Tier | Price | Features |
|------|-------|----------|
| 🟠 Community | FREE | All 11 pages, donate button |
| ⚡ Personal | 20,000 sats (~$13) | Command Palette, collapsing sidebar, CSV export, Health Score |
| 🏢 Pro | 9,000 sats/month | Everything + plugins, multi-node, webhooks, Docker, AI assistant |

Get a license at **satslist.shop** — pay with Bitcoin Lightning ⚡

---

## Requirements

- Linux (Ubuntu/Debian recommended)
- LND node with `lncli` access
- Python 3.9+ (bare metal) or Docker

---

## Features

- 📊 Real-time dashboard
- ⚡ Channel management
- 🔀 Routing analytics
- 💳 Wallet & transactions
- ⛏️ Mining fleet monitor
- 🔔 Alerts system
- 📓 Node journal
- ⚙️ Settings & security

---

Made with ⚡ and ₿ for the Bitcoin community
