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
19. [Channel Strategy (Pro)](#channel-strategy-pro)
21. [Themes](#themes)
21. [Command Palette (Personal+)](#command-palette-personal)
22. [How Lightning Routing Works (Tutorial)](#how-lightning-routing-works-tutorial)
23. [Channel Management Tips](#channel-management-tips)
24. [Fee Optimization Guide](#fee-optimization-guide)
25. [Rebalancing Guide](#rebalancing-guide)
26. [Auto-Reconnect](#auto-reconnect-background-worker)
27. [Tax Accounting Export](#tax-accounting-export-pro)
28. [Troubleshooting](#troubleshooting)
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
- **🌊 Draining badge** — shown when Drain & Trap is active and channel is draining at low PPM
- **🪤 Trapped badge** — shown when fee has spiked to trap PPM because local balance hit the floor
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

- **Add entry** — title, body, tag (milestone/issue/note/win), block number auto-captured
- **Click any entry** — opens full text in a modal for easy reading
- **Tags** — color-coded: milestone (purple), win (green), issue (red), note (gray)
- **Delete** — trash icon on each entry card
- Entries are immutable by design — the journal is a permanent log, not an editable document

---

## Node P&L (Treasury Page)

The P&L card at the top of the Treasury page shows your node profitability at a glance.

- **Routing Fees** — total sats earned forwarding payments
- **Rebalance Fees** — sats spent on circular rebalancing
- **Open Fees (est.)** — estimated channel opening costs from LND commit fees
- **Close Fees** — confirmed cooperative close fees
- **Net P&L** — routing fees minus all costs (green = profitable, red = still recovering)
- **Time periods** — 30 Cal-Days (rolling 30 days), 1 Year, All Time

> ⚠️ Opening/closing fees are approximated from LND data. Verify exact fees via mempool.space using the channel funding txid.

---
## Alerts

Custom notification system for channel status changes and routing activity thresholds.

- **Disk warnings** — system disk alerts at 80% (warning) and 90% (critical) before node crashes
- **Bitcoin disk** — separate alert for blockchain data drive
- **Browser notifications** — enable in Settings to get push notifications for critical alerts even when LCC is in background tab
- Checks run every 60 seconds automatically

---

## Umbrel Installation

LCC is submitted to the Umbrel App Store (pending approval). For beta access, sideload manually.

See **UMBREL.md** in the repo for step-by-step instructions, or paste this into Claude:
> *"I want to sideload Lightning Control Center (LCC) on my Umbrel node. Please guide me step by step."*

---
## Settings

- **Password** — change LCC login password
- **Energy Calculator** — enter electricity rate (cents/kWh), server wattage (W), and current BTC price (USD) to calculate energy cost in the P&L card
- **Alert notifications** — enable browser push notifications for critical alerts
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
Yes! Way simpler. Here's the tutorial text — copy and paste it into MANUAL.md on GitHub, right before the "## Channel Management Tips" section:

---

## How Lightning Routing Works (Tutorial)

Understanding how payments route through your node is the most important concept for a node operator.

### Your Node is a Hallway

Think of your node as a hallway with doors on each side. Each door is a channel to another node. A payment enters through one channel and leaves through another. You collect a fee for letting it pass through.

### Channel Labels vs Routing Direction

These are two DIFFERENT things that confuse most new node runners:

**Channel label (You opened / Peer opened):**
- This tells you WHO created the channel - it never changes
- "You opened" = you funded it with your sats
- "Peer opened" = they funded it with their sats
- Traffic flows BOTH directions regardless of who opened it

**Routing direction (Unwetter → LNBiG):**
- This tells you which way a specific payment traveled
- The first name is where the payment came FROM
- The second name is where the payment went TO
- This changes with every payment

**Example:** "Routed Unwetter → LNBiG Hub-3" means:
1. A payment arrived at your node FROM Unwetter
2. Your node forwarded it OUT through LNBiG Hub-3
3. You earned a fee for the forwarding

### How Liquidity Moves

Every time a payment routes through your node, liquidity shifts. The incoming channel GAINS local balance (sats move to your side). The outgoing channel LOSES local balance (sats leave your side).

### Why Channels Get Stuck

A channel gets stuck when all the liquidity is on one side (98% local). Payments can only flow OUT through this channel. There is almost no room for payments to flow IN. If ALL your channels are stuck like this, payments cannot route through your node.

### What Rebalancing Does

Rebalancing moves sats from a full channel to an empty one using a circular payment through the Lightning Network. After rebalancing, BOTH channels can route payments in both directions.

### When to Rebalance

Rebalance WHEN:
- A profitable routing channel is stuck above 90% local
- The rebalance fee is less than what you will earn from routing
- Traffic was flowing before the channel got stuck

Do NOT rebalance when:
- Fees are at 0 PPM — you earn nothing back
- The channel never routes anyway — wasted money
- You are rebalancing just to make the bar look even

### The Fee and Liquidity Relationship

Your fees control which direction liquidity flows:
- LOW fees (50 PPM) = attracts lots of traffic, channel drains fast
- HIGH fees (500 PPM) = less traffic, channel drains slowly
- VERY HIGH fees (1200 PPM) = almost no traffic, channel preserves balance

This is exactly what Drain and Trap automates:
1. Drain at 50 PPM — channel empties through routing
2. Trap at 1200 PPM — channel stops draining, slowly refills
3. Repeat automatically

---

Paste that right above "## Channel Management Tips" in your MANUAL.md on GitHub! Then `git pull` on the ProDesk to sync. 🟠

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

## Auto-Reconnect (Background Worker)

LCC automatically reconnects dropped channel peers every 30 minutes. No configuration needed — runs as a background worker alongside Drain & Trap and the auto-rebalancer.

How it works:
- Compares connected peers vs channel peers every 30 minutes
- If a channel peer is disconnected, looks up their address and reconnects
- Logs reconnections to console
- Keeps your channels active without manual intervention

---

## Tax Accounting Export (Pro)

Download a tax-ready CSV of all node activity from the Treasury page.

Click the green **📥 Tax CSV** button on the P&L card to download. The CSV includes:
- **routing_income** — sats earned from forwarding payments
- **payment_sent** — Lightning payments with fees
- **channel_open** — on-chain fees for opening channels
- **channel_close** — funds returned from closed channels
- **energy_cost** — estimated electricity cost (from Settings energy calculator)

Each row includes: date, type, amount (sats), fee (sats), description, and transaction ID.

After download, a summary popup shows total routing income, fees paid, energy costs, and net P&L.

---

## Channel Strategy (Pro)

The Channel Strategy page gives you a bird's-eye view of every channel's health — automatically scored by combining your local balance, your fee rate, and your peer's fee rate into a color-coded action plan.

**Opening the page:** Click **Strategy** in the sidebar — it opens as a clean floating window so you can keep using the rest of LCC alongside it.

**Auto-refreshes every 60 seconds** — no manual refresh needed.

---

### Summary Cards

| Card | What it means |
|------|--------------|
| Total Channels | All active channels |
| Keep (Inbound) | Peer-opened channels providing inbound liquidity — don't touch |
| Drain | Your channels that are too full — push sats out |
| Monitor | Watch these — borderline fee situation |
| Close Candidates | Dead weight — peer fee too high, consider exiting |

---

### Color Code

| Color | Assessment | Action |
|-------|-----------|--------|
| 🔵 Blue | Inbound lifeline | Keep as-is — this is free inbound liquidity |
| 🟢 Green | Low peer fee | Drain aggressively at 10-25 ppm |
| 🟠 Orange | Moderate / Monitor | Adjust fees, watch routing flow |
| 🔴 Red | Close candidate | CLOSE or Loop Out — peer fee too high to be useful |

---

### Columns Explained

- **Channel** — peer alias + who opened the channel (You opened / Peer opened)
- **Capacity** — total channel size in sats
- **Local %** — how much of the channel balance is on your side
- **Your Fee** — your current fee rate in PPM (milli-msat per sat routed)
- **Peer Fee** — your peer's fee rate in PPM
- **Assessment** — LCC's diagnosis of the channel health
- **Action / Target Fee** — recommended next step

---

### What is Loop Out?

When LCC recommends **CLOSE / Loop Out** it means the peer fee is too high (>500 PPM) and the channel isn't earning. Loop Out is an alternative to closing:

- Sends your sats **out via Lightning** to a swap service (Boltz, Lightning Loop)
- Swap service sends the equivalent **back to your on-chain wallet**
- Channel stays open with fresh inbound space
- Fee: ~0.5% + on-chain mining fee

**Easiest option:** [boltz.exchange](https://boltz.exchange) — no account, no KYC.

> 💡 Try rebalancing first — it's cheaper. Use Loop Out only when all channels are too full and there's nowhere to rebalance into.

---

## Channel Strategy (Pro)

Opens as a clean floating window — keep it running alongside the rest of the app. Auto-refreshes every 60 seconds.

**Open it:** Click **Strategy** in the sidebar.

### Summary Cards

| Card | Meaning |
|------|---------|
| Total Channels | All active channels |
| Keep (Inbound) | Peer-opened channels — free inbound liquidity, don't touch |
| Drain | Your channels that are too full — push sats out |
| Monitor | Borderline situation — watch closely |
| Close Candidates | Dead weight — peer fee too high, consider exiting |

### Color Code

| Color | Assessment | Action |
|-------|-----------|--------|
| 🔵 Blue | Inbound lifeline | Keep as-is |
| 🟢 Green | Low peer fee | Drain aggressively at 10-25 ppm |
| 🟠 Orange | Moderate | Adjust fees, monitor routing |
| 🔴 Red | Close candidate | CLOSE or Loop Out |

### Columns

- **Local %** — how much balance is on your side
- **Your Fee** — your current PPM
- **Peer Fee** — your peer's PPM (drives the recommendation)
- **Assessment** — LCC's diagnosis
- **Action** — recommended next step

### What is Loop Out?

When LCC recommends **CLOSE / Loop Out** the peer fee is too high (>500 PPM) and the channel isn't earning.

Loop Out is an alternative to closing — sends sats out via Lightning to a swap service (Boltz), which sends the equivalent back to your on-chain wallet. Channel stays open with fresh inbound space. Fee: ~0.5% + mining fee.

> 💡 Try rebalancing first — it's cheaper. Use Loop Out only when all channels are too full and there's nowhere to rebalance into.

**Easiest option:** [boltz.exchange](https://boltz.exchange) — no account, no KYC.

---

## Troubleshooting

**LCC shows no data:** Check lncli getinfo, restart LCC, check logs

**Channels inactive:** Peer might be offline, try disconnect/reconnect

**Wallet shows 0 or NaN:** LND might be down, check lncli walletbalance

**Disk space issues:** Check df -h, truncate large syslogs, set up logrotate

**Treasury NaN:** LNbits invoice key missing from data.json

---

## Remote Access Options

### Option 1 — LAN Only (Home Network)
Access LCC at `http://your-server-ip:8765` — works only when you're on the same network.

### Option 2 — Tailscale (Recommended — Private)
Encrypted access from anywhere with no third party seeing your traffic.

1. Install Tailscale on your node: `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`
2. Install Tailscale on your phone/laptop (App Store or tailscale.com)
3. Log in with the same account on both devices
4. Access LCC at `http://[tailscale-ip]:8765` from anywhere

Free for personal use. End-to-end encrypted. No ports exposed.

### Option 3 — Cloudflare Tunnel (Easy but Less Private)
Cloudflare sits between you and your node — convenient but they can see your traffic. Follow the Cloudflare Tunnel setup guide to expose LCC at a custom domain.

### Option 4 — Tor (Maximum Privacy)
Coming soon — access LCC via .onion address for maximum privacy.

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
