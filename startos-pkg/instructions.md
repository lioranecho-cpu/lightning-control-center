# Lightning Control Center — Start9 Edition

## Requirements

- **LND** must be installed and running on your Start9 server. LCC will not start without it.
- **Bitcoin Core** is optional. When installed, LCC shows live mempool data and fee estimates.

## Getting Started

1. Install LND from the Start9 Marketplace if you haven't already.
2. Install Lightning Control Center.
3. Open the **Web Interface** link — it opens your LCC dashboard at `/dashboard`.

## Tiers

LCC has three tiers:

| Tier | Cost | Features |
|------|------|----------|
| Community | Free | Dashboard, channels, routing, wallet, journal |
| Personal | 20,000 sats (one-time) | + Auto-rebalance, drain/trap strategies, P&L, accounting |
| Pro | 9,000 sats/month | + NWC wallet connect, advanced analytics |

To upgrade, purchase a license key at **satslist.shop** and enter it in the Settings → License page inside LCC.

## Data Storage

All your data (channel journal, auto-rebalance settings, NWC connections) is stored on your Start9 server's encrypted volume. It persists across updates and restarts.

## LND Connection

LCC connects to your Start9 LND instance automatically using the internal bridge network. No configuration needed.

## Bitcoin Core (Optional)

If Bitcoin Core is installed and running, LCC will show:
- Live mempool size and congestion
- Fee-per-vbyte estimates

If Bitcoin Core is not installed, the mempool section shows "not available."

## Loop (Lightning Loop)

Lightning Loop (for on-chain ↔ Lightning liquidity swaps) is **not available** in the Start9 edition. All Loop endpoints return a "not available" message.

## Support

- GitHub: https://github.com/lioranecho-cpu/lightning-control-center
- Shop / upgrades: https://satslist.shop
