# ⚡ LCC — Lightning Control Center
## Complete User Manual

**Sparkie Labs** — *Ignite. Control. Build.*

> 💡 **Quick Help:** Paste this into any AI (Claude, ChatGPT, Grok) for interactive support:
> *"Read https://github.com/lioranecho-cpu/lightning-control-center and help me with [your question]"*

*Manual for LCC v0.2.2*

---

## Table of Contents

**Pages**
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
11. [Node P&L (Treasury Page)](#node-pl-treasury-page)
12. [Alerts](#alerts)
13. [Settings](#settings)
14. [Integrations](#integrations)
15. [NWC — Nostr Wallet Connect (Pro)](#nwc--nostr-wallet-connect-pro)
16. [Treasury (Pro)](#treasury-pro)
17. [Umbrel Installation](#umbrel-installation)

**Liquidity and fee tools**

18. [Inbound Health](#inbound-health)
19. [Channels With the Same Peer (Peer Groups)](#channels-with-the-same-peer-peer-groups)
20. [Drain and Trap Strategy (Pro)](#drain-and-trap-strategy-pro)
21. [Auto Fee by Liquidity (Pro)](#auto-fee-by-liquidity-pro)
22. [Fee Recommendations (Pro)](#fee-recommendations-pro)
23. [Channel Strategy (Pro)](#channel-strategy-pro)
24. [Rebalancing (Pro)](#rebalancing-pro)
25. [Loop In and Loop Out (Pro)](#loop-in-and-loop-out-pro)
26. [Live HTLC Stream (Pro)](#live-htlc-stream-pro)
27. [Auto-Reconnect](#auto-reconnect-background-worker)
28. [Tax Accounting Export (Pro)](#tax-accounting-export-pro)

**Guides**

29. [How Lightning Routing Works (Tutorial)](#how-lightning-routing-works-tutorial)
30. [Liquidity Playbook: Refill, Rebalance or Recycle?](#liquidity-playbook-refill-rebalance-or-recycle)
31. [Channel Management Tips](#channel-management-tips)
32. [Fee Optimization Guide](#fee-optimization-guide)
33. [Routing Pattern Analysis](#routing-pattern-analysis)

**Other**

34. [Themes](#themes)
35. [Command Palette (Personal+)](#command-palette-personal)
36. [Troubleshooting](#troubleshooting)
37. [Remote Access Options](#remote-access-options)
38. [Security Notes](#security-notes)
39. [Subscription Tiers](#subscription-tiers)

---

## Getting Started

### Requirements
- Linux (Ubuntu/Debian recommended)
- LND node with lncli access, synced and running
- Bitcoin Core running and synced
- Python 3.9+
- Optional: Lightning Loop (built into litd) for Loop In / Loop Out

### Installation
```bash
curl -sSL https://raw.githubusercontent.com/lioranecho-cpu/lightning-control-center/main/install.sh | bash
```

After installation, open your browser and go to http://your-server-ip:8765

### First Login
- The login password is stored in data.json — change it in Settings after the first login
- Pro tier supports Nostr login via NIP-07 (Alby, nos2x) or nsec key

### Automations are off by default
Auto Rebalance, Auto Fee, Drain & Trap and fee changes never run until you switch them on for a channel. LCC never opens or closes a channel by itself.

---

## Dashboard

Your command center — everything at a glance.

**Summary Cards:** Total Capacity, Active Channels, Routing Fees (30D), Routed Volume (30D), Wallet Balance

**Charts:** Routing Fees over time, Routed Volume over time

**Active Channels Table:** Peer name, capacity, local/remote balance, fee PPM, status — sorted by capacity

**Inbound Health card:** how easy it is for others to pay through you. See [Inbound Health](#inbound-health).

**Node Health:** Bitcoin Core, LND, RTL, LNbits, Mining Pool status and uptime

**Status Bar:** Bitcoin price, mempool size, fee rate, peer count, UTC time

---

## Channels

Manage your Lightning channels — open, close, update fees, rebalance, Loop.

- **Inbound/Outbound labels** — "🔓 You opened (outbound)" or "🔑 Peer opened (inbound)"
- **Balance bar** — local vs remote balance as a percentage
- **Sort dropdown** — Capacity, Inbound first, Outbound first, Most full, Most empty, Fee PPM, Name
- **Tabs** — Active, Pending, All
- **Peer groups** — when you have 2 or more channels with the same peer, they are shown together under one 🔗 peer card. See [Peer Groups](#channels-with-the-same-peer-peer-groups).

**Top buttons:**
- **🎯 Targeted Rebalance** — you pick the source and destination
- **⚖️ Rebalance All Channels** — moves sats from full channels to empty ones, with a profit-based fee cap
- **🔄 Loop Monitor** — swap history in a popup

**Per-channel actions:**
- **Update Fees** — change base fee and fee PPM
- **🔄 Loop Out** — move sats from this channel to your on-chain wallet
- **⬇️ Loop In** — refill this channel from your on-chain wallet
- **🔁 Auto Rebalance** — scheduled rebalancing for this channel (Pro)
- **💰 Auto Fee** — fee follows the channel's balance (Pro)
- **Rebalance** — one rebalance run for this channel
- **Peer Policy** — your fees vs your peer's fees side by side
- **⚡ Strategy** — set Drain and Trap (Pro)
- **Close Channel** — cooperative close with double confirmation (never a force close)

**Badges and status lines:**
- **🌊 Draining** — Drain & Trap is active and the channel is draining at low PPM
- **🪤 Trapped** — fee has jumped to the trap PPM because local balance hit the floor
- **Auto Rebal / Auto Fee** — shows the current settings, or OFF

---

## Peers

Manage your network connections.

- **Connected Peers** — every node you are connected to
- **Connect New Peer** — enter pubkey@host:port
- **Disconnect** — drops the connection (the channel stays open and reconnects automatically)

---

## Routing

Full forwarding history.

- **Forwarding History table** — timestamp, amount, fee earned, in channel, out channel
- **Pagination** — 25 events per page
- **Sort** — Newest or Oldest first
- **Time filters** — 1 day, 7 days, 30 days, All
- **Export CSV** — download routing data (Personal+)

---

## Wallet

Send and receive, on-chain and Lightning.

**Receive On-chain:** New Address creates a fresh bc1 address with QR code

**Receive Lightning:** Lightning Address with QR code

**Send Payment:** Paste a Lightning invoice (lnbc...) or on-chain address (bc1...), set amount and fee limit, confirm before sending

**Recent Transactions:** Filter by type (All, Received, Sent, Forwarded, On-chain, Rebalances only), Hide Rebalances checkbox. Rebalances show named pairs, e.g. "Rebalance: block-iad-1 → LNBiG [Hub-3]", with the fee inline.

---

## Analytics

- **Routing Fees Over Time** — daily earnings (7D, 30D, 90D, All)
- **Fee Projections** — estimated daily, weekly, monthly, yearly earnings
- **Top Routing Pairs** — routes ranked by fees earned, with event count and volume. Each row shows which channel's outbound fee policy is charging (base msat / PPM). The outgoing channel always sets the fee for a route, not the incoming one.
- **Routed Volume** — daily volume chart
- **Rebalance ROI Tracker (Pro)** — see [Rebalancing](#rebalance-roi-tracker)
- **Fee Recommendations (Pro)** — see [Fee Recommendations](#fee-recommendations-pro)

---

## Mining

Monitor your mining fleet — miner names, hashrate, power use, IP addresses, pool connection status.

---

## System Monitor

Service health: Bitcoin Core, LND, Lightning Terminal, RTL, LNbits, Mining Pool, Uptime.

---

## Node Journal

A timestamped log of your node: your own notes plus everything LCC's automations do.

**Organized by day**
- Entries are grouped by day — **Today** is open, older days are folded. Click a day to open it.
- Each day header shows a short summary (rebalances and fees paid, fee changes, Loops, notes, alerts).
- The last 7 days are shown. Click **Show older days** to load 7 more.

**Filter chips:** All · Loop · Fees · Rebalance · Alerts · Notes (each with a count)

**Robot entries are bundled:** 3 or more automatic entries in a row (💰 Auto Fee adjusted, 🔀 Auto-rebalance, 📊 ROI checks) collapse into one line you can expand.

**Your own entries**
- **Add entry** — title, body, tag (milestone / win / issue / note); block height is captured automatically
- **Click any entry** to read it in full
- **Delete** — trash icon on each entry
- Entries can't be edited — the journal is a permanent log

---

## Node P&L (Treasury Page)

The P&L card at the top of the Treasury page shows your node's profit at a glance.

- **Routing Fees** — sats earned forwarding payments
- **Rebalance Fees** — sats spent on circular rebalancing
- **Open Fees (est.)** — estimated channel opening costs from LND commit fees
- **Close Fees** — confirmed cooperative close fees
- **Net P&L** — routing fees minus all costs (green = profitable, red = still recovering)
- **Time periods** — 30 days, 1 Year, All Time

> ⚠️ Opening/closing fees are estimated from LND data. Check exact fees on mempool.space using the funding txid.

---

## Alerts

- **Disk warnings** — at 80% (warning) and 90% (critical) before the node crashes
- **Bitcoin disk** — separate alert for the blockchain drive
- **Browser notifications** — enable in Settings to get critical alerts while LCC is in a background tab
- Checks run every 60 seconds

---

## Settings

- **Password** — change the LCC login password
- **Energy Calculator** — electricity rate (cents/kWh), server wattage (W) and BTC price, used for energy cost in the P&L card
- **Alert notifications** — browser push notifications for critical alerts
- **Auto-Rebalance Schedule (Pro)** — Off/Manual, every 6/12/24/48 hours
- **Rebalance Amount** — 10k, 30k, 50k or 100k sats per operation (also the most Rebalance All moves per channel)

**Environment settings (.env)**
- `LCC_ONCHAIN_RESERVE` — sats LCC always leaves in your on-chain wallet. Loop In refuses any swap that would go below it. Default: 1,000,000.

---

## Integrations

Visual map of all LCC integrations. Connected features have green borders. Shows Connected, Coming Soon, Planned and Pro features.

---

## NWC — Nostr Wallet Connect (Pro)

Connect any NWC-compatible wallet (Zeus, Alby, Damus) directly to your node.

1. Go to the NWC page and create a new connection
2. Scan the QR or paste the connection string into your wallet app
3. The wallet talks directly to your node — no custodian

Supports: get_info, get_balance, make_invoice, lookup_invoice, list_transactions

---

## Treasury (Pro)

One balance view across your node and connected wallets: Total Balance, LNbits wallet, Add Wallet for more NWC wallets, Live Payment Feed.

---

## Umbrel Installation

LCC is submitted to the Umbrel App Store (pending approval). For beta access, sideload manually.

See **UMBREL.md** in the repo for step-by-step instructions, or paste this into Claude:
> *"I want to sideload Lightning Control Center (LCC) on my Umbrel node. Please guide me step by step."*

---

## Inbound Health

A Dashboard card that answers one question: **how easy is it for others to send payments through you?**

To route, payments must first come **in** to your node. That needs **room to receive**: the remote balance on your channels (sats on your peer's side). Lightning Labs' "Hard to Reach" label means your node is in the bottom 15% for inbound efficiency — this card shows why and what to do.

**What the card shows**
- **Room to receive** — total remote balance, and its % of your capacity
- **Largest share** — the peer holding the most of that room, and its %
- **Senders (7d) nearly full** — channels that sent you traffic in the last 7 days but now have under 10% room left
- **Channel bars** — busiest senders first. Bar = room that peer has to send to you. ppm = what that peer charges to send to you. ⚠️ = a recent sender that is nearly full.
- **💡 Hints** — what to do next

**Status badge**

| Badge | When |
|-------|------|
| 🔴 Hard to reach | Half or more of your recent senders are nearly full, **or** one peer holds 60%+ of your room |
| 🟡 Tight | Any recent sender is nearly full, **or** one peer holds 40%+ of your room |
| 🟢 Easy to reach | Room is spread well across your senders |

**How to fix it**
- **Busy senders nearly full:** give them a low fee (Drain & Trap) so traffic leaves through them and frees room again.
- **One peer holds most of the room:** add inbound from more peers — channels other nodes open to you, LN+ swaps, or bought inbound. Don't remove the big peer; add others.

---

## Channels With the Same Peer (Peer Groups)

When you have 2 or more channels with the same peer, LND treats them as **one pipe**. A payment going to that peer can use whichever channel has room (non-strict forwarding). So it makes sense to manage them together.

**On the Channels page** they appear under one 🔗 peer card, with the member channels indented below it:
- **Combined** capacity, local balance and fill %
- **Fees:** "on all ✓" when every channel has the same fee, or ⚠️ **mixed** when they differ. Mixed fees on one peer make routing unpredictable.
- **⚡ Set fee for all** — one base fee and PPM on every channel with that peer
- **💰 Auto Fee for all** — one Auto Fee band on every channel with that peer. The fee then follows the **combined** balance, so all channels always show the same price.

**On the Strategy page** a 🔗 row shows the combined capacity, local %, fees and 7-day traffic, with the member channels indented under it.

**Tips**
- Judge a peer as a whole, not by its single channels. One full and one empty channel to the same peer is normal.
- A Loop In through a peer refills the group — you choose the peer, not the channel.
- Closing one channel of a group only shrinks the pipe. For peers that opened channels to you (bought inbound), see the [Liquidity Playbook](#liquidity-playbook-refill-rebalance-or-recycle) before closing.

---

## Drain and Trap Strategy (Pro)

Automated per-channel fee strategy.

**The Cycle:**
1. **Drain Phase** — channel runs at low PPM (e.g. 50) to attract volume
2. The channel drains as payments flow through
3. When local balance hits the Floor % (e.g. 2-3%), the worker notices
4. **Trap Phase** — fee jumps to high PPM (e.g. 1200) for premium payments
5. When the balance recovers, the fee drops back to drain mode
6. Checked every 5 minutes

**Setup:** Channels page → ⚡ Strategy → Drain and Trap → set Drain PPM, Trap PPM and Floor %

**Best practices:**
- Use on channels that are full and should drain — including busy senders that are nearly full on the [Inbound Health](#inbound-health) card
- Do NOT use on inbound channels you paid for — give those a fixed, higher PPM or a tight Auto Fee band
- Don't run Drain & Trap and Auto Fee (or any outside fee robot) on the same channel — they will fight
- Strategy events show up in the Live Stream

---

## Auto Fee by Liquidity (Pro)

Adjusts a channel's fee automatically based on its local balance.

- Set min/max base fee, min/max PPM and a check interval in hours
- **High local balance** (full of your sats) → fee moves toward the **minimum** to attract routing
- **Low local balance** (drained) → fee moves toward the **maximum** to slow the drain and earn more per sat
- Only updates the fee when the calculated value changes, and keeps the channel's real `time_lock_delta`
- Runs on its own, separate from Auto Rebalance
- Enable from the 💰 Auto Fee button; enter -1 at the first prompt to disable
- Every change is logged to the Node Journal

**Grouped Auto Fee:** on a 🔗 peer card, **💰 Auto Fee for all** sets the same band on every channel with that peer and uses their **combined** balance. See [Peer Groups](#channels-with-the-same-peer-peer-groups).

**Tight bands for refilled exits:** Auto Fee follows balance, not demand. On a channel you refill with Loop In and that sells fast, use a narrow band near the price you know sells (for example 925–1250 ppm instead of 100–1250), so it never gives your refill away cheap.

---

## Fee Recommendations (Pro)

PPM suggestions on the Analytics page.

- Analyzes top routing pairs by events per day
- **High demand:** Raise PPM on [channel]
- **Low activity at low PPM:** already low — check liquidity balance
- **Low activity at high PPM:** Lower PPM on [channel]
- Healthy channels are hidden — only actionable advice is shown

---

## Channel Strategy (Pro)

A bird's-eye view of every channel, color-coded with a recommended action. Open **Strategy** in the sidebar — it opens in its own window and refreshes every 60 seconds.

### Color Code

| Color | Meaning | Typical action |
|-------|---------|----------------|
| 🔵 Blue | Peer opened, not full — inbound lifeline | Keep as-is |
| 🟢 Green | Full (90%+ local) but your fee is still above 50 ppm | Lower the fee so traffic can leave |
| 🟠 Orange | Monitor: balanced, nearly empty, high peer fee, or being watched for recycle | Watch, adjust fees, refill if it sells |
| 🔴 Red | Recycle candidate, or high peer fee with no traffic | Cooperative close / Loop Out |

### Columns

- **Channel** — peer alias + who opened it
- **Capacity**, **Local %**
- **Your Fee / Peer Fee** — PPM
- **Routed 7d (out / in)** — sats that left / arrived through this channel in the last 7 days
- **Assessment** and **Action / Target Fee**
- **🔗 rows** — combined view for channels with the same peer

### Recycle logic

A channel becomes a **recycle candidate** when it is **stuck**:
1. 95%+ local, **and**
2. your fee is already low (50 ppm or less), **and**
3. nothing routed out in the last 7 days.

LCC then watches it. During the watch it is orange ("day X of 7"). If it is still stuck after **7 days**, it turns red with the numbers:
- **Close cost** — about 200 vbytes × the current mempool fee rate. The node that **opened** the channel pays it, so if the peer opened it, the peer pays.
- **Loop Out cost** — about 0.35% of the local balance, for comparison.

A cooperative close returns your sats on-chain for just the mining fee — usually far cheaper than a Loop Out. Use the sats for a Loop In into a busy exit, or a channel to a peer that sends you traffic.

> ⚠️ Closing is permanent and loses that peer. Check the channel isn't a sender you still need. LCC never closes channels by itself.

---

## Rebalancing (Pro)

Rebalancing is a circular payment from your node back to your node: sats leave through a full channel and come back in through an empty one. You pay routing fees to the nodes in between.

**The golden rule:** a rebalance only pays if the fee you pay is less than what the refilled channel will earn when those sats leave again. LCC now enforces this everywhere.

### The fee cap (all rebalances)

LCC never pays more than **half of what the receiving channel earns**:

> **fee cap = amount × receiving channel's ppm × 0.5 ÷ 1,000,000**

Example: refilling 100,000 sats into a channel that charges 1,000 ppm. It will earn 100 sats when those sats sell, so LCC pays at most 50 sats.

- A channel at **0 ppm** earns nothing — LCC skips it ("too little to pay for a rebalance").
- If no route is cheaper than the cap, **nothing is paid**. You'll see "no route under the fee cap".

### ⚖️ Rebalance All Channels

1. Sources: channels **above 80%** local. Exits: channels **below 20%** local.
2. Exits are tried best-earning first; sources fullest first.
3. Amount per move: the smaller of (source down to 50%), (exit up to 50%) and the Settings rebalance amount. Moves under 1,000 sats are skipped.
4. One successful move per exit, and at most **10 tries** per press.

The result is honest, for example:
- `✅ 2 moved (100,000 sats, −38 sats fees) · 3 found no route under the fee cap`
- `ℹ️ 0 moved · 8 found no route under the fee cap · 1 skipped`

Hover the message for each attempt's details. The page reloads only if something moved.

### 🎯 Targeted Rebalance

You choose exactly where sats come from and where they go.

1. Click **🎯 Targeted Rebalance**
2. Pick the **source** (a full channel) and **destination** (an empty one). The table shows each channel's local % and **your fee** on it.
3. Enter the amount. **Max fee** fills in automatically (half of what the destination earns). You can change it.
4. Read the verdict box:
   - ✅ **Profitable** — max fee is half or less of what the destination earns
   - ⚠️ **Thin margin** — you keep only a little after the fee
   - ❌ **Will lose money** — max fee is above what the destination earns, or it charges 0 ppm. LCC suggests a max fee and points to Loop In.
5. Execute. Losing rebalances ask "This will likely lose money. Proceed anyway?"

On success LCC shows the fee in sats **and ppm** next to what the destination earns.

**"No profitable route right now"** means nothing reached that channel under your max fee. Nothing was paid. Don't just raise the cap — if the destination is a busy hub, a [Loop In](#loop-in-and-loop-out-pro) is usually much cheaper.

### 🔁 Per-Channel Auto Rebalance

Automatic rebalancing for one channel, with its own amount, schedule and fee limit.

**Enable:** 🔁 Auto Rebalance on a channel card → amount (enter 0 to disable) → interval hours or scheduled hours → max fee.

**How it works**
- Checked every hour, in **interval** mode (every X hours) or **scheduled** mode (at set hours, e.g. 8 and 21)
- Runs only if the channel is more than 10 points above its target (default target 50%, so above 60% local)
- Sends sats to a channel that is below 20% local
- Fee limit = the **smaller** of your max fee and the profit-based cap above
- 3 failures in a row switch it off automatically, with a journal warning

**Card badge:** OFF · 🔄 6h · 10k · max 400s · ⏰ 8,21:00 · 20k · max 400s · ❌ 2/3 (failures so far)

**Tips**
- Small amounts (10k) find cheap routes more often — but the cap scales with the amount, so a 10k move into a 1,000 ppm channel can pay at most 5 sats.
- Only automate channels whose exits earn well. Into big sinks (e.g. LNBiG), circular rebalancing rarely finds a profitable route — use Loop In.
- Watch the journal for a day before enabling more channels.

### Rebalance ROI Tracker

On the Analytics page under Top Routing Pairs. For each channel it compares:
- **Rebalance Cost** — sats spent on rebalances
- **Routing Earned** — routing fees earned through that channel

**Net ROI** = earned − cost. Filters: 24h, 7d, 30d, All.

- High earned + low cost = your best channels
- Cost but no routing = stop rebalancing them
- Consider closing channels that stay negative after 21 days

### When NOT to rebalance
- The destination charges 0 ppm or very little
- The destination is a liquidity sink that costs more to reach than it earns
- The channel never routes anyway
- Just to make the balance bar look even

---

## Loop In and Loop Out (Pro)

Loop swaps move sats between your channels and your on-chain wallet without closing anything. LCC uses Lightning Labs' Loop (built into litd, found automatically). The ⬇️ / 🔄 buttons only appear when Loop is available.

| | ⬇️ Loop In | 🔄 Loop Out |
|---|---|---|
| Direction | On-chain wallet → channel | Channel → on-chain wallet |
| Use it to | Refill a drained channel that sells well | Empty a full channel that won't drain |
| Needs | On-chain sats | Local balance in the channel |
| Typical cost (seen on a live node) | About 340–370 sats per 1M | About 0.35–0.40% (3,500–4,000 sats per 1M) |

Loop In is usually **much cheaper** than both Loop Out and rebalancing into a busy hub.

### ⬇️ Loop In
1. Click **⬇️ Loop In** on a drained channel that earns well
2. Enter the amount and click **Get Fee Quote** — LCC shows the total cost in sats and ppm, your on-chain balance and what's left after
3. Read the verdict: ✅ **Worth it** (cost is half or less of what the channel charges), ⚠️ **Thin margin** (only worth it if it sells quickly), or a warning that it costs more than the channel earns
4. Confirm. The sats arrive in the channel **through that peer**.

- You pick the **peer**, not the exact channel. With several channels to one peer, the sats can land in any of them.
- **On-chain reserve:** LCC refuses a Loop In that would leave less than `LCC_ONCHAIN_RESERVE` (default 1,000,000 sats) on-chain, so you always keep sats for closes and fee bumps.
- The sats you swap in become Lightning balance — they are not lost. You earn them back (plus profit) as they route out.
- After a refill, price the channel by **sell speed**: if it empties within hours, raise the fee next time; if it sits, lower it.

### 🔄 Loop Out
1. Click **🔄 Loop Out** on a full channel
2. Enter the amount and confirm target, click **Get Fee Quote**
3. Check the **Real cost** (Loop's quote + the routing estimate, in sats and ppm), set the **max routing fee**, then confirm

**Why there are two fees:** Loop's quote covers the swap and on-chain fee, but **not** the Lightning routing fee to reach the Loop server. LCC estimates that routing fee from this channel and lets you cap it, so the real cost never surprises you.

**Before you Loop Out a stuck channel**, check the [Channel Strategy](#recycle-logic) page — a cooperative close is often far cheaper.

### Requirements
- Loop available (built into litd; LCC finds the `loop` binary automatically)
- The Loop server sets a minimum swap size — LCC shows an error below it
- Swap server: Lightning Labs

### Loop Monitor
Click **🔄 Loop Monitor** on the Channels page (or the link after starting a swap). It shows every swap with channel names, times and status badges: INITIATED, IN PROGRESS, SUCCESS, FAILED. Refreshes every 30 seconds. Pending swaps show their quoted fee; finished swaps show the real cost.

### Auto-Journal
Every swap started from LCC is logged to the Node Journal: channel, amount, swap ID and block height.

---

## Live HTLC Stream (Pro)

Real-time routing monitor — companion app on port 8001.

- Live feed of forwarding events: time, amount, path, result, fee earned
- Strategy events highlighted in orange
- Events persist across reloads, with a Clear button
- Open from the sidebar or Command Palette

---

## Auto-Reconnect (Background Worker)

LCC checks every 30 minutes whether any channel peer has disconnected, looks up its address and reconnects. No setup needed.

---

## Tax Accounting Export (Pro)

Click **📥 Tax CSV** on the Treasury P&L card. The CSV includes:
- **routing_income** — sats earned forwarding
- **payment_sent** — Lightning payments with fees
- **channel_open** — on-chain fees for opening channels
- **channel_close** — funds returned from closed channels
- **energy_cost** — from the Settings energy calculator

Each row: date, type, amount (sats), fee (sats), description, transaction ID. A summary popup shows routing income, fees, energy and net P&L.

---

## How Lightning Routing Works (Tutorial)

Understanding how payments move through your node is the most important concept for a node operator.

### Your Node is a Hallway

Think of your node as a hallway with doors. Each door is a channel to another node. A payment comes in one door and leaves through another. You collect a fee for letting it through.

### Channel Labels vs Routing Direction

These are two DIFFERENT things:

**Channel label (You opened / Peer opened):**
- Tells you WHO created the channel — it never changes
- "You opened" = you funded it with your sats
- "Peer opened" = they funded it with their sats
- Traffic flows BOTH ways no matter who opened it

**Routing direction (Unwetter → LNBiG):**
- Tells you which way one payment traveled
- First name = where it came FROM; second = where it went TO
- Changes with every payment

**Example:** "Routed Unwetter → LNBiG Hub-3" means a payment came in from Unwetter, left through LNBiG Hub-3, and you earned a fee.

### How Liquidity Moves

Every routed payment shifts liquidity. The incoming channel GAINS local balance. The outgoing channel LOSES local balance.

### Why Channels Get Stuck

A channel is stuck when almost all of it is on one side. At 98% local, payments can only go OUT through it — there's no room for payments to come IN. If all your channels are like this, nothing can route through you.

### What Rebalancing Does

Rebalancing sends sats from a full channel around the network back into an empty one. Both channels can then route again — but you pay fees to do it. See [Rebalancing](#rebalancing-pro).

### The Fee and Liquidity Relationship

Your fees steer liquidity:
- LOW fees (50 PPM) = lots of traffic, the channel drains fast
- HIGH fees (500 PPM) = less traffic, drains slowly
- VERY HIGH fees (1200 PPM) = almost no traffic, the balance stays

Drain and Trap automates this: drain at a low fee, then trap at a high fee when nearly empty.

---

## Liquidity Playbook: Refill, Rebalance or Recycle?

Simple rules learned from running a real routing node.

### 1. Drained channel that sells well → refill it
- **First choice: Loop In** (about 350 sats per 1M). Cheap, and you choose the peer.
- **Rebalance only if** the [fee cap](#the-fee-cap-all-rebalances) finds a route. Into busy hubs it usually won't.
- Then price by demand: raise the fee if it sells out fast, lower it if it sits.

### 2. Full channel that won't drain → let it drain, then recycle
1. Lower its fee (Drain & Trap or a low fixed fee).
2. Wait — the Strategy page watches it for 7 days.
3. Still stuck at a low fee with nothing routed out? **Cooperative close** it and reuse the sats. That's usually far cheaper than a Loop Out.

### 3. Drained channel you opened, peer not worth refilling → close and reopen elsewhere
Closing a near-empty channel you opened costs only the mining fee. Open a fresh channel where the traffic is.

### 4. Bought inbound (the peer opened it) → keep it
- Closing returns only **your** small side; the peer takes back theirs, and you lose inbound you paid for (and maybe what's left of a paid term).
- Don't close and re-buy to "refresh" it. If you want to sell into that peer, open **your own** channel to it. LND treats both as one pipe ([Peer Groups](#channels-with-the-same-peer-peer-groups)).
- Too much of your inbound from one peer? Add inbound from others; don't remove it.

### 5. Never
- Force-close a channel unless the peer is gone for good
- Run two fee robots on the same channel
- Spend your last on-chain sats — keep a reserve for closes and fee bumps

### Cost cheat sheet

| Action | Typical cost | Good for |
|--------|-------------|----------|
| Loop In | ~350 sats per 1M | Refilling a busy, well-paid exit |
| Cooperative close | ~200 vbytes × fee rate, paid by the channel opener | Recycling stuck channels |
| Rebalance | Up to half of what the exit earns (LCC cap) | Small corrections when a cheap route exists |
| Loop Out | ~0.35–0.40% | Emptying a channel you want to keep open |

Costs vary with the mempool and the network — always check the quote.

---

## Channel Management Tips

### Inbound vs Outbound
- Outbound (you opened) — your sats; they drain as payments route out
- Inbound (they opened) — gives you room to receive

### Choosing Peers
- Connect to well-connected nodes (LNBiG, ACINQ, block-iad-1)
- Check peer fees — high peer fees mean less traffic coming FROM them
- Diversify across peers — check the [Inbound Health](#inbound-health) card
- Check uptime on Amboss or 1ML

### Channel Sizing
- Minimum useful: 500,000 sats
- Sweet spot: 1-5M sats
- Maximum: 16,777,215 sats (unless both nodes support large channels)

### More channels = more work
Every channel needs fees and liquidity care. A few well-chosen, well-sized channels often earn more than many small ones.

---

## Fee Optimization Guide

### Understanding Fees
- **Base Fee (msat)** — flat fee per payment. **0 recommended** — many wallets (Phoenix, Zeus and others) avoid routes with a base fee
- **Fee PPM** — fee per million sats. 100 PPM = 100 sats per 1M routed

### Strategy by Channel Type
- **Bought inbound / refilled exits to busy hubs:** high, demand-based fee (often 800-1,250 ppm), fixed or a tight Auto Fee band
- **Full outbound channels:** low fee to drain, or Drain and Trap
- **Channels with the same peer:** one fee for all ([Peer Groups](#channels-with-the-same-peer-peer-groups))
- **High demand routes:** raise PPM gradually

### General Rules
- 0 base fee + variable PPM is the modern standard
- Change fees in steps and give each change time to work (a day for busy channels, longer for quiet ones)
- Use Peer Policy to compare your fees with your peer's
- Price by how fast the channel sells, not just by how full it is

---

## Routing Pattern Analysis

Find your node's busiest hours to time your rebalances and refills.

1. Export your routing CSV from the Routing page (All time)
2. Ask Claude or any AI: *"Analyze this routing CSV and show me hourly and daily patterns — when does my node route the most?"*

**Look for:** peak hours with the most fees, dead hours, weekday vs weekend patterns.

**Use it:** schedule per-channel auto rebalance (or do Loop Ins) about 1 hour before your peaks. Example: peaks at 9-11 AM and 10-11 PM → run at 8 AM and 9 PM.

You need at least 2 weeks of data. Re-check monthly as your channels change.

---

## Themes

4 built-in themes — Midnight (dark blue), Obsidian (pure black), Amber (warm gold), Forest (deep green). Switch from the sidebar footer; your choice is remembered.

---

## Command Palette (Personal+)

Press Ctrl+Space on any page. Type to search pages and commands. Quick actions: Copy Pubkey, Open SatsList, Launch Live Stream.

---

## Troubleshooting

**LCC shows no data:** check `lncli getinfo`, restart LCC, check logs

**Channels inactive:** the peer may be offline — try disconnect/reconnect

**Wallet shows 0 or NaN:** LND may be down — check `lncli walletbalance`

**Disk space issues:** check `df -h`, truncate large syslogs, set up logrotate

**Treasury NaN:** LNbits invoice key missing from data.json

**Rebalance says "no route under the fee cap" / "No profitable route right now":** no route was cheap enough to make money. Nothing was paid. Try a smaller amount, a different source, or Loop In.

**Rebalance All says "skipped":** the exit charges too little (e.g. 0 ppm) to pay for a rebalance, or the 10-try limit was reached.

**Many old failed payments slowing things down:** failed rebalance attempts pile up in LND. Clear them with `lncli deletepayments --all` (failed payments only, unless you add `--include_non_failed`).

**Loop buttons missing:** Loop isn't available on this node (needs litd or loopd).

**Loop In refused because of the reserve:** the swap would leave less than `LCC_ONCHAIN_RESERVE` on-chain. Use a smaller amount or add on-chain funds.

**Peer group shows "mixed" fees:** click ⚡ Set fee for all on the 🔗 peer card.

---

## Remote Access Options

### Option 1 — LAN Only (Home Network)
`http://your-server-ip:8765` — only on the same network.

### Option 2 — Tailscale (Recommended — Private)
Encrypted access from anywhere, no third party sees your traffic.

1. On your node: `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`
2. Install Tailscale on your phone/laptop
3. Log in with the same account on both
4. Open `http://[tailscale-ip]:8765`

Free for personal use. End-to-end encrypted. No open ports.

### Option 3 — Cloudflare Tunnel (Easy but Less Private)
Cloudflare sits between you and your node — convenient, but they can see your traffic.

### Option 4 — Tor (Maximum Privacy)
Coming soon.

---

## Security Notes

- Keep LCC LAN-only, on Tailscale, or behind a tunnel — never expose port 8765 directly
- Store RPC credentials in the .env file, never in source code
- Change the default password after installation
- Use Nostr login (NIP-07) for browser extension security
- Never share your seed, macaroons (other than read-only) or wallet passwords with anyone — including AI assistants

---

## Subscription Tiers

| Tier | Price | Highlights |
|------|-------|------------|
| Community | FREE | Full dashboard, all pages, 4 themes |
| Personal | 20,000 sats one-time | Command Palette, CSV export, Health Score, per-channel fees, channel opening |
| Pro | 9,000 sats/month or 90,000 sats/year | Automation: Drain and Trap, Auto Fee, Auto Rebalance, Loop, NWC, Live Stream, Fee Recs |

Get a license at **satslist.shop** — pay with Bitcoin Lightning.

---

**Sparkie Labs** — *Bitcoin sovereignty for everyone, not just developers.*

MIT License
