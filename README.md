# ⚡ Lightning Control Center (LCC)

> **A beautiful, self-hosted dashboard for managing your Bitcoin Lightning node.**

LCC replaces the need for multiple apps — RTL, mempool.space, spreadsheets, and terminal windows — with one clean, fast, browser-based interface that runs on your own hardware.

---

## ✨ Features

| Page | What it does |
|------|-------------|
| 🏠 **Dashboard** | At-a-glance overview — channels, routing fees, wallet balance, node health |
| ⚡ **Channels** | Channel management with balance bars, pending LN+ rings, fee settings |
| 👥 **Peers** | Connected peers with ⚡ channel badges, ping times, bytes sent/recv |
| 🔀 **Routing** | Forwarding history, fee earnings, fee policy management |
| 👛 **Wallet** | On-chain + Lightning balances, receive address generation, transaction history |
| 📊 **Analytics** | Routing income charts, fee projections, top routing pairs |
| 📓 **Node Journal** | Personal log for node events, milestones and decisions |
| 🔔 **Alerts** | Automated monitoring — channel skew, low balance, mempool fees, service health |
| ⛏️ **Mining** | ASIC fleet overview — hashrate gauges, pool status, efficiency ratings |
| 🖥️ **System** | ProDesk hardware health — CPU, RAM, disk, uptime, all services |
| ⚙️ **Settings** | Password, session, fee defaults, node identity, display preferences |

---

## 🖼️ Screenshots

> Dashboard · Channels · Alerts · Mining · System

*(Add screenshots here)*

---

## 🏗️ Architecture

```
Browser (HTML/CSS/Vanilla JS)
        ↓
FastAPI Backend (Python)
        ↓
lncli + bitcoin-cli
        ↓
LND (litd) + Bitcoin Core
```

- **Frontend:** Pure HTML5 / CSS3 / Vanilla JS — no framework, no build step
- **Backend:** Python FastAPI wrapping `lncli` and `bitcoin-cli` commands
- **Auth:** Password-protected with configurable session timeout
- **Access:** Local network or remote via Cloudflare Tunnel
- **Theme:** Dark navy — easy on the eyes for long node operator sessions

---

## 🚀 Quick Start

### Prerequisites

- Ubuntu 20.04+ (or similar Linux)
- Python 3.10+
- LND running (standalone or via litd)
- Bitcoin Core running

### Installation

```bash
# Clone the repo
git clone https://github.com/lioranecho-cpu/lightning-control-center.git
cd lightning-control-center

# Install dependencies
pip3 install fastapi uvicorn aiofiles psutil --break-system-packages

# Configure your node connection (edit lcc_api.py)
nano lcc_api.py
# Set your bitcoin-cli path and RPC credentials

# Start LCC
uvicorn lcc_api:app --host 0.0.0.0 --port 8765
```

Open your browser at `http://localhost:8765/dashboard`

Default password: **change this in `login.html` before deploying!**

```javascript
// In login.html, find and update:
const LCC_PASSWORD_HASH = 'your-secure-password';
```

### Run as a systemd service (recommended)

```bash
sudo nano /etc/systemd/system/lcc.service
```

```ini
[Unit]
Description=Lightning Control Center
After=network.target litd.service

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/lcc
ExecStart=/home/YOUR_USER/.local/bin/uvicorn lcc_api:app --host 0.0.0.0 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable lcc
sudo systemctl start lcc
```

---

## 🔧 Configuration

Edit `lcc_api.py` to match your setup:

```python
# Bitcoin Core path (snap install)
BITCOIN_CLI = '/snap/bitcoin-core/current/bin/bitcoin-cli'
BITCOIN_RPC_USER = 'your-rpc-user'
BITCOIN_RPC_PASS = 'your-rpc-password'

# LND connects automatically via default macaroon path
```

### Remote Access via Cloudflare Tunnel

```yaml
# ~/.cloudflared/config.yml
ingress:
  - hostname: lcc.yourdomain.com
    service: http://localhost:8765
  - service: http_status:404
```

---

## 🔒 Security

- All pages require password authentication
- Sessions expire after 4 hours by default (configurable)
- Auto-logout checks run every 5 minutes on open tabs
- Basic auth via Caddy recommended for additional protection
- **Never expose LCC directly to the internet without auth**

---

## ⚡ Editions

| Feature | 🟠 Community | ⚡ Personal | 🏢 Pro |
|---------|------------|------------|--------|
| All 11 pages | ✅ | ✅ | ✅ |
| Single node | ✅ | ✅ | ✅ |
| Multi-node | ❌ | ❌ | ✅ |
| Donate button | ✅ | ❌ | ❌ |
| SatsList link | ✅ | Configurable | Configurable |
| Priority support | ❌ | ❌ | ✅ |
| License | MIT | Commercial | Commercial |

**Community Edition** is free and open source. Personal and Pro editions available on [SatsList](https://satslist.shop) — paid in sats, no fiat required.

---

## 🗺️ Roadmap

- [ ] LNURL-Auth login (sign with your node key)
- [ ] One-click channel rebalancing
- [ ] Command palette (Cmd+K)
- [ ] Node health score (0-100)
- [ ] Auto-journal on significant events
- [ ] CSV export for routing history
- [ ] Telegram/Discord webhook alerts (Pro)
- [ ] Docker Compose for Umbrel/Start9/RaspiBlitz
- [ ] Liquidity Manager (Loop/Boltz integration)
- [ ] Multi-node support (Pro)

---

## 🤝 Contributing

LCC is built by a solo node operator for the Bitcoin community. PRs welcome — especially for:
- Bug fixes
- New miner support (Antminer, Whatsminer)
- Additional lncli endpoint coverage
- UI improvements

---

## 📄 License

Community Edition: **MIT License** — free to use, modify and distribute.

---

## ⚡ Built by

[SatsList](https://satslist.shop) — The Bitcoin-only P2P marketplace. Buy, sell, stack sats.

Made with ⚡ and ₿ for the Bitcoin community.

---

*If LCC earns you routing fees, consider sending a few sats to the donate button. Every sat counts.* 🟠
