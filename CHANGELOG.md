# Changelog

All notable changes to LCC — Lightning Control Center.

## Unreleased (v0.2.3)

### Added
- **Current on-chain fees in Open and Close Channel** — No priority / Low / Medium / High from mempool.space (or Bitcoin Core), one click to use, or type your own, with a short note on speed vs. cost. Close Channel is now a window that shows what comes back to your wallet, who pays the closing fee, and the fee in sats.
- **Channel fee when opening** — set the ppm from the start (base fee 0), so new channels no longer start at LND's default 1 ppm. It matches your other channels with that peer, and the new channel joins their Auto Fee group.
- **🎚️ Rebalance cap setting** — choose the most a rebalance may cost as a share of what the receiving channel earns: 50% default, 100% break-even, up to 150%. Used by Targeted Rebalance, Rebalance All and per-channel Auto Rebalance.

### Changed
- **Open Channel shows the real result** — LCC read the wrong field of LND's answer, so a channel that opened fine was reported as failed. Fixed.
- **No accidental double opens** — one open per peer at a time, and a warning if a channel to that peer is already waiting for confirmation.
- **Open Channel fee rate is used** — the sat/vB you enter is now sent to LND (it was ignored before). Leave it empty and LND picks the rate.
- **Strategy page** — "lower your fee" only appears when your fee is above the suggested range; full channels at a low fee show "price isn't the problem" and join the 7-day recycle watch.
- **Targeted Rebalance runs in the background** — LCC answers at once and the page checks every 3 seconds, with a ⏳ box showing the two channels and a timer. Survives a page reload; starting the same pair twice follows the running one. No more "Can't reach LND … Read timed out" on long searches.
- **Longer route search** — 5 minutes instead of 90 seconds.
- **Multi-part payments** — payments and rebalances can split into up to 16 parts over different routes (same as lncli).
- **Clearer results** — "still in progress" for a slow route, "No route found within 5 minutes. Nothing was paid." for a real timeout.
- **Manual** — Auto Fee: how the fee is calculated, what it does not do (it follows balance, not routing activity) and how to fine-tune it.

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
