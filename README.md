# ⚡ Lightning Control Center (LCC)
**The dashboard for the Bitcoin sovereign stack.**

A beautiful, self-hosted Lightning node manager. Built for Bitcoin node runners.

**Live demo:** https://lcc.satslist.shop/dashboard

---

## 📖 Need Help?

Paste this into any AI (Claude, ChatGPT, Grok) for an interactive walkthrough:

> *"Read https://github.com/lioranecho-cpu/lightning-control-center and walk me through its features, installation, and usage as a Lightning node operator. Include tips on channel management, fee optimization, and rebalancing strategies."*

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

## Requirements

- Linux (Ubuntu/Debian recommended)
- LND node with `lncli` access
- Bitcoin Core running and synced
- Python 3.9+ (bare metal) or Docker

---

## Features

### 🟠 Community (Free)
- 📊 Real-time dashboard — node health, block height, sync status
- ⚡ Channel management — view, open, close channels with inbound/outbound labels
- 👥 Peer management — connect, disconnect peers
- 💳 Wallet — on-chain & Lightning send/receive with QR codes
- 🔀 Routing — forwarding history with pagination, sorting, peer aliases
- 📈 Analytics — fees earned, routed volume, daily charts, top routing pairs
- 📓 Node journal — personal notes and logs
- 🔔 Alerts — custom notifications
- ⛏️ Mining dashboard — hashrate, pool stats
- 🖥️ System monitor — LND, Bitcoin Core, RTL, LNbits status
- 🔗 Integrations overview
- 🎨 4 themes — Midnight, Obsidian, Amber, Forest

### ⚡ Personal (20,000 sats one-time)
- Everything in Community, plus:
- ⌨️ Command Palette (Ctrl+Space)
- 📁 Collapsing sidebar
- 📊 Per-channel fee updates
- 🔓 Channel opening UI
- ❤️ Health score
- 📥 CSV export

### 🔥 Pro (9,000 sats/month or 90,000 sats/year)
- Everything in Personal, plus:
- 🟣 **NWC (Nostr Wallet Connect)** — connect Zeus, Alby, Damus and any NWC app
- 💡 **Fee Recommendations** — data-driven PPM suggestions with current channel fees
- 🌊 **Drain & Trap** — automated fee strategy per channel (drain PPM, trap PPM, floor %)
- ⚖️ **Auto-rebalance scheduler** — set interval and amount
- 🔀 **Manual rebalance** — per-channel with fee estimate
- 📡 **Live HTLC Stream** — real-time routing event monitor (companion app)
- 🔐 **Nostr login** — NIP-07 (Alby, nos2x) or nsec
- 💰 **Treasury + NWC wallet** — connect any NWC wallet
- 👤 **Peer Policy viewer** — see your fees vs peer fees per channel
- 📥 **CSV export** — wallet and routing data

---

## 💎 Coming Soon
- 🖥️ Hardware node connectivity — Umbrel, RaspiBlitz, Start9, myNode
- 🔌 Plugin architecture — extend LCC
- 💰 Multi-wallet Treasury — unified balance across multiple wallets
- 📦 One-click installer

---

## Tiers

| Tier | Price | Highlights |
|------|-------|------------|
| 🟠 Community | FREE | Full dashboard, 4 themes |
| ⚡ Personal | 20,000 sats (~$13) | Command Palette, CSV, Health Score |
| 🔥 Pro | 9,000 sats/month | NWC, Drain & Trap, Live Stream, Fee Recs |

Get a license at **satslist.shop** — pay with Bitcoin Lightning ⚡

---

## Screenshots

*Coming soon*

---

**Sparkie Labs** — *Ignite. Control. Build.*

Made with ⚡ and ₿ for the Bitcoin community

MIT License
