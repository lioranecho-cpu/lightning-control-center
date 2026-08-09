# ⚡ LCC — Lightning Control Center
## Complete User Manual

**Sparkie Labs** — *Ignite. Control. Build.*

> 💡 **Quick Help:** Paste this into any AI (Claude, ChatGPT, Grok) for interactive support:
> *"Read https://github.com/lioranecho-cpu/lightning-control-center and help me with [your question]"*

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard](#dashboard)
3. [Channels](#channels)
4. [Peers](#peers)
5. [Routing](#routing)
6. [Wallet](#wallet)
7. [Analytics](#analytics)
8. [Mining](#mining)
9. [System Monitor](#system-monitor)
10. [Node Journal](#node-journal)
11. [Alerts](#alerts)
12. [Settings](#settings)
13. [Integrations](#integrations)
14. [NWC — Nostr Wallet Connect (Pro)](#nwc--nostr-wallet-connect-pro)
15. [Treasury (Pro)](#treasury-pro)
16. [Drain and Trap Strategy (Pro)](#drain-and-trap-strategy-pro)
17. [Live HTLC Stream (Pro)](#live-htlc-stream-pro)
18. [Fee Recommendations (Pro)](#fee-recommendations-pro)
19. [Themes](#themes)
20. [Command Palette (Personal+)](#command-palette-personal)
21. [Channel Management Tips](#channel-management-tips)
22. [Fee Optimization Guide](#fee-optimization-guide)
23. [Rebalancing Guide](#rebalancing-guide)
24. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Requirements
- Linux (Ubuntu/Debian recommended)
- LND node with lncli access, synced and running
- Bitcoin Core running and synced
- Python 3.9+

### Installation
```bash
curl -sSL https://raw.githubusercontent.com/lioranecho-cpu/lightning-control-center/main/install.sh | bash
```

After installation, open your browser and navigate to http://your-server-ip:8765

### First Login
- Default login uses a password stored in data.json
- Pro tier supports Nostr login via NIP-07 (Alby, nos2x) or nsec key

---

## Dashboard

Your command center — everything at a glance.

**Summary Cards:** Total Capacity, Active Channels, Routing Fees (30D), Routed Volume (30D), Wallet Balance

**Charts:** Routing Fees over time, Routed Volume over time

**Active Channels Table:** Peer name, capacity, local/remote balance, fee PPM, status — sorted by capacity

**Node Health:** Bitcoin Core, LND, RTL, LNbits, Mining Pool status and uptime

**Status Bar:** Bitcoin price, mempool size, fee rate, peer count, UTC time

---

## Channels

Manage your Lightning channels — open, close, update fees, rebalance.

- **Inbound/Outbound labels** — every channel shows Outbound (you opened) or Inbound (they opened to you)
- **Balance bar** — visual local vs remote balance percentage
- **Sort dropdown** — Capacity, Inbound first, Outbound first, Most full, Most empty, Fee PPM
- **Tabs** — Active, Pending, All

**Per-channel actions:**
- **Update Fees** — change base fee and fee PPM per channel
- **Rebalance** — manual circular rebalance
- **Peer Policy** — view your fees vs your peer fees side by side
- **Strategy** — set Drain and Trap automation (Pro)
- **Close Channel** — cooperative close with double confirmation

---

## Peers

Manage your network connections.

- **Connected Peers** — list of all nodes you are connected to
- **Connect New Peer** — enter pubkey@host:port to connect
- **Disconnect** — drop connection (channel stays open, reconnects automatically)

---

## Routing

Full forwarding history with detailed analytics.

- **Forwarding History table** — timestamp, amount, fee earned, in channel, out channel
- **Pagination** — 25 events per page with Prev/Next
- **Sort** — Newest first or Oldest first
- **Time filters** — Last 1 day, 7 days, 30 days, All
- **Export CSV** — download routing data (Personal+)

---

## Wallet

Full Bitcoin wallet — send and receive, on-chain and Lightning.

**Receive On-chain:** Click New Address to generate a fresh bc1 address with QR code

**Receive Lightning:** Lightning Address shown with QR code

**Send Payment:** Paste a Lightning invoice (lnbc...) or on-chain address (bc1...), set amount and fee limit, confirmation dialog before sending

**Recent Transactions:** Filter by type (All, Received, Sent, Forwarded, On-chain, Rebalances only), Hide Rebalances checkbox, rebalance fees shown inline

---

## Analytics

Deep insights into your routing performance.

- **Routing Fees Over Time** — daily earnings with time filters (7D, 30D, 90D, All)
- **Fee Projections** — estimated daily, weekly, monthly, yearly earnings
- **Top Routing Pairs** — routes ranked by fees earned with event count and volume
- **Routed Volume** — daily BTC volume chart
- **Fee Recommendations (Pro)** — actionable PPM suggestions per channel

---

## Mining

Monitor your Bitcoin mining fleet — miner names, hashrate, power consumption, IP addresses, pool connection status.

---

## System Monitor

Service health: Bitcoin Core, LND, Lightning Terminal, RTL, LNbits, Mining Pool, Uptime.

---

## Node Journal

Personal timestamped notes and logs for tracking channel opens, fee changes, and routing observations.

---

## Alerts

Custom notification system for channel status changes and routing activity thresholds.

---

## Settings

- **Password** — change LCC login password
- **Auto-Rebalance Schedule (Pro)** — Off/Manual, Every 6/12/24/48 hours
- **Rebalance Amount** — 10k, 30k, 50k, or 100k sats per operation

---

## Integrations

Visual map of all LCC integrations. Connected features have green borders. Shows Connected, Coming Soon, Planned, and Pro Features.

---

## NWC — Nostr Wallet Connect (Pro)

Connect any NWC-compatible wallet (Zeus, Alby, Damus) directly to your node.

1. Go to NWC page and create a new connection
2. Scan QR or paste connection string into your wallet app
3. Wallet connects directly to your node — no custodian

Supports: get_info, get_balance, make_invoice, lookup_invoice, list_transactions

---

## Treasury (Pro)

Unified balance view across your node and connected wallets. Total Balance, LNbits wallet, Add Wallet for additional NWC wallets, Live Payment Feed.

---

## Drain and Trap Strategy (Pro)

Automated per-channel fee strategy — the feature that sets LCC apart.

**The Cycle:**
1. **Drain Phase** — channel runs at low PPM (e.g., 50) to attract volume
2. Channel drains naturally as payments flow through
3. When local balance hits the Floor % (e.g., 2-3%), the worker detects it
4. **Trap Phase** — fees spike to high PPM (e.g., 1200) for premium payments
5. When balance recovers, fees drop back to drain mode
6. Cycle repeats automatically every 5 minutes

**Setup:** Channels page, click Strategy, select Drain and Trap, set Drain PPM, Trap PPM, and Floor %

**Best practices:**
- Use on outbound channels that drain naturally
- Do NOT use on inbound channels you paid for — set those to manual with higher PPM
- Strategy events broadcast to the Live Stream

---

## Live HTLC Stream (Pro)

Real-time routing event monitor — companion app on port 8001.

- Live WebSocket feed of forwarding events
- Obsidian theme (pure black background)
- Shows timestamp, amount, routing path, outcome, fee earned
- Strategy events highlighted in orange
- Events persist across reloads with Clear button
- Access via sidebar or Command Palette

---

## Fee Recommendations (Pro)

Data-driven PPM suggestions in Analytics page.

- Analyzes top routing pairs by events per day
- Shows current PPM per channel
- High demand: Raise PPM on [channel] (currently X PPM)
- Low activity at low PPM: already low, check liquidity balance
- Low activity at high PPM: Lower PPM on [channel]
- Healthy channels hidden — only actionable advice shown

---

## Themes

4 built-in themes — Midnight (dark blue), Obsidian (pure black), Amber (warm gold), Forest (deep green). Switch from sidebar footer, persists via localStorage.

---

## Command Palette (Personal+)

Press Ctrl+Space from any page. Type to search pages and commands. Quick actions: Copy Pubkey, Open SatsList, Launch Live Stream.

---

## Channel Management Tips

### Inbound vs Outbound
- Outbound (you opened) — your sats drain as payments route through
- Inbound (they opened) — you have receiving capacity

### Choosing Peers
- Connect to well-connected hubs (LNBiG, ACINQ, block-iad-1)
- Check peer fee policies — high peer fees mean less traffic FROM them
- Diversify across multiple peers
- Check uptime on Amboss or 1ML

### Channel Sizing
- Minimum useful: 500,000 sats
- Sweet spot: 1-5M sats
- Maximum: 16,777,215 sats (protocol limit)

---

## Fee Optimization Guide

### Understanding Fees
- **Base Fee (msat)** — flat fee per payment. 0 recommended
- **Fee PPM** — proportional fee per million sats. 100 PPM = 100 sats per 1M routed

### Strategy by Channel Type
- Inbound channels: 200-500 PPM to preserve paid liquidity
- Outbound channels: 50-100 PPM or Drain and Trap
- High demand routes: raise PPM gradually

### General Rules
- 0 base fee + variable PPM is modern standard
- Do not change fees more than once per week
- Use Peer Policy viewer to compare your fees vs peer fees

---

## Rebalancing Guide

### When to Rebalance
- A profitable channel is drained below 5% local
- Rebalancing fee is less than expected routing earnings

### When NOT to Rebalance
- Channel fees are at 0 PPM
- Rebalancing fee exceeds expected earnings
- Auto-rebalancer running at high frequency

### Cost Control
- Typical fees: 50-200 sats per 50k operation
- Check wallet for actual fees: rebalance (circular) (-X sats fee)
- Set to Off/Manual in Settings to prevent runaway costs

---

## Troubleshooting

**LCC shows no data:** Check lncli getinfo, restart LCC, check logs

**Channels inactive:** Peer might be offline, try disconnect/reconnect

**Wallet shows 0 or NaN:** LND might be down, check lncli walletbalance

**Disk space issues:** Check df -h, truncate large syslogs, set up logrotate

**Treasury NaN:** LNbits invoice key missing from data.json

---

## Security Notes

- Keep LCC LAN-only or behind Cloudflare Tunnel
- Store RPC credentials in .env file, never in source code
- Change default passwords after installation
- Use Nostr login (NIP-07) for browser extension security

---

## Subscription Tiers

| Tier | Price | Highlights |
|------|-------|------------|
| Community | FREE | Full dashboard, 4 themes |
| Personal | 20,000 sats one-time | Command Palette, CSV, Health Score |
| Pro | 9,000 sats/month | NWC, Drain and Trap, Live Stream, Fee Recs |

Get a license at **satslist.shop** — pay with Bitcoin Lightning

---

**Sparkie Labs** — *Bitcoin sovereignty for everyone, not just developers.*

MIT License
