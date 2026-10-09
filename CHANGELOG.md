# Changelog

All notable changes to LCC — Lightning Control Center.

## v0.2.2 — 2026-10-09

### Added
- **Loop In** — refill a drained channel from your on-chain wallet, through the peer you choose. Fee quote before you confirm; refuses swaps that would leave less than `LCC_ONCHAIN_RESERVE` on-chain (default 1,000,000 sats).
- **Inbound Health card** on the Dashboard — room to receive, largest share, senders nearly full, and hints. Status: Easy to reach / Tight / Hard to reach.
- **Peer groups** — channels with the same peer are shown together (combined balance, fee check). New "Set fee for all" and "Auto Fee for all"; grouped Auto Fee follows the combined balance. Also shown on the Strategy page.
- **Strategy recycle logic** — stuck channels (95%+ local, fee ≤50 ppm, nothing routed out) are watched for 7 days, then flagged with close cost vs Loop Out cost. New "Routed 7d (out / in)" column.
- **Targeted Rebalance verdict** — shows your fee per channel, fills in a profitable max fee, and warns before a rebalance that will lose money.

### Changed
- **Rebalance fee cap** — Rebalance All, Targeted and per-channel Auto Rebalance never pay more than half of what the receiving channel earns. Channels at 0 ppm are skipped. Rebalance All tries at most 10 routes per press, best-earning exits first.
- **Honest rebalance results** — e.g. "2 moved (100,000 sats, −38 sats fees) · 3 found no route under the fee cap" instead of counting attempts as successes.
- **Loop Out** — shows an estimate of the routing fee to the Loop server (not in Loop's own quote) and lets you cap it; `loop` binary found automatically.
- **Node Journal** — grouped by day with summaries, filter chips (Loop, Fees, Rebalance, Alerts, Notes), automatic entries bundled, 7 days shown with "Show older".
- **"No profitable route right now"** message replaces "try increasing max fee".
- **Manual** — cleaned up and updated for all of the above, plus a new Liquidity Playbook.

## Earlier versions
See the GitHub release tags (v0.2.0, v0.2.1 and older).
