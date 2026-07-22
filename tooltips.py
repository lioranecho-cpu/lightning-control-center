# Tooltip injection script
# Adds tooltip CSS + JS to all LCC pages and wraps key elements with tooltips

import os
import re

files = [
    '/home/luca/lcc/index.html',
    '/home/luca/lcc/wallet.html',
    '/home/luca/lcc/channels.html',
    '/home/luca/lcc/routing.html',
    '/home/luca/lcc/peers.html',
    '/home/luca/lcc/analytics.html',
    '/home/luca/lcc/journal.html',
    '/home/luca/lcc/alerts.html',
    '/home/luca/lcc/mining.html',
]

TOOLTIP_CSS = '''
  /* ── TOOLTIPS ── */
  .tip{position:relative;cursor:help;}
  .tip::after{
    content:attr(data-tip);
    position:absolute;
    bottom:calc(100% + 8px);
    left:50%;
    transform:translateX(-50%);
    background:#0a0d14;
    color:#f0f0f0;
    border:1px solid #252d3d;
    border-radius:8px;
    padding:8px 12px;
    font-size:11px;
    font-family:'Inter',system-ui,sans-serif;
    line-height:1.5;
    width:220px;
    text-align:center;
    white-space:normal;
    pointer-events:none;
    opacity:0;
    transition:opacity .15s;
    z-index:9999;
    box-shadow:0 4px 20px rgba(0,0,0,.5);
  }
  .tip:hover::after{opacity:1;}
  .tip-right::after{left:auto;right:0;transform:none;}
  .tip-left::after{left:0;transform:none;}
'''

# Page-specific tooltip replacements
REPLACEMENTS = {
    'index.html': [
        # Stat card labels
        ('TOTAL CAPACITY', '<span class="tip" data-tip="Total sats locked across all open Lightning channels on your node">TOTAL CAPACITY</span>'),
        ('ACTIVE CHANNELS', '<span class="tip" data-tip="Number of open Lightning channels ready to send and receive payments">ACTIVE CHANNELS</span>'),
        ('ROUTING FEES (30D)', '<span class="tip" data-tip="Sats earned in the last 30 days by forwarding other people\'s Lightning payments through your node">ROUTING FEES (30D)</span>'),
        ('ROUTED VOLUME (30D)', '<span class="tip" data-tip="Total value of payments forwarded through your node in the last 30 days">ROUTED VOLUME (30D)</span>'),
        ('WALLET BALANCE', '<span class="tip" data-tip="Your on-chain Bitcoin balance available to open new channels or withdraw">WALLET BALANCE</span>'),
        # Node health labels
        ('>Bitcoin Core<', '><span class="tip" data-tip="Bitcoin Core is the full node that validates blocks and transactions">Bitcoin Core</span><'),
        ('>LND / litd<', '><span class="tip" data-tip="Lightning Network Daemon — manages your payment channels and routes Lightning payments">LND / litd</span><'),
        ('>Lightning Terminal<', '><span class="tip" data-tip="Lightning Terminal (litd) — combines LND with Loop, Pool and Faraday services">Lightning Terminal</span><'),
    ],
    'channels.html': [
        ('TOTAL CAPACITY', '<span class="tip" data-tip="Combined capacity of all open channels in sats">TOTAL CAPACITY</span>'),
        ('LOCAL BALANCE', '<span class="tip" data-tip="Sats on your side — what you can send outbound through your channels">LOCAL BALANCE</span>'),
        ('REMOTE BALANCE', '<span class="tip" data-tip="Sats on the peer\'s side — what you can receive through your channels">REMOTE BALANCE</span>'),
        ('>Fee PPM<', '><span class="tip" data-tip="Parts Per Million fee rate. 100 ppm = 0.01% of payment amount. You earn this on every payment routed through this channel">Fee PPM</span><'),
        ('>Local<', '><span class="tip" data-tip="Your local balance — sats you can send outbound">Local</span><'),
        ('>Remote<', '><span class="tip" data-tip="Remote balance — sats you can receive inbound">Remote</span><'),
    ],
    'peers.html': [
        ('>Bytes Sent<', '><span class="tip" data-tip="Total bytes of Lightning gossip and routing data sent to this peer">Bytes Sent</span><'),
        ('>Bytes Recv<', '><span class="tip" data-tip="Total bytes of Lightning gossip and routing data received from this peer">Bytes Recv</span><'),
        ('>Ping<', '><span class="tip" data-tip="Round-trip response time to this peer in milliseconds. Lower is better for routing">Ping</span><'),
        ('Channel badge', ''),  # handled separately
    ],
    'routing.html': [
        ('Fees Earned (30D)', '<span class="tip" data-tip="Total sats earned by forwarding Lightning payments through your node in the last 30 days">Fees Earned (30D)</span>'),
        ('Routed Volume (30D)', '<span class="tip" data-tip="Total value of payments forwarded through your node in BTC">Routed Volume (30D)</span>'),
        ('Routing Events', '<span class="tip" data-tip="Number of individual payments forwarded through your node">Routing Events</span>'),
        ('Avg Fee Per Route', '<span class="tip" data-tip="Average sats earned per forwarded payment. Increases as you raise your fee rate">Avg Fee Per Route</span>'),
        ('BASE FEE (MSAT)', '<span class="tip" data-tip="Fixed fee in millisatoshis charged per payment regardless of amount. 1000 msat = 1 sat">BASE FEE (MSAT)</span>'),
        ('FEE RATE (PPM)', '<span class="tip" data-tip="Variable fee as parts per million of payment amount. 100 ppm = 0.01% = 1 sat per 10,000 sats routed">FEE RATE (PPM)</span>'),
        ('TIME LOCK DELTA', '<span class="tip" data-tip="CLTV delta — number of blocks added to payment timelock when forwarding. Standard is 40">TIME LOCK DELTA</span>'),
    ],
    'wallet.html': [
        ('TOTAL BALANCE', '<span class="tip" data-tip="Combined on-chain + Lightning channel balance in sats">TOTAL BALANCE</span>'),
        ('ON-CHAIN BALANCE', '<span class="tip" data-tip="Bitcoin held in your LND on-chain wallet. Use this to open new Lightning channels">ON-CHAIN BALANCE</span>'),
        ('CHANNEL BALANCE', '<span class="tip" data-tip="Sats locked in your Lightning channels. Spendable instantly via Lightning payments">CHANNEL BALANCE</span>'),
    ],
    'analytics.html': [
        ('Total Fees Earned', '<span class="tip" data-tip="All routing fees earned since your node started routing payments">Total Fees Earned</span>'),
        ('Total Volume Routed', '<span class="tip" data-tip="Total value of all payments forwarded through your node">Total Volume Routed</span>'),
        ('Routing Events', '<span class="tip" data-tip="Total number of individual Lightning payments forwarded">Routing Events</span>'),
        ('Avg Fee Per Route', '<span class="tip" data-tip="Average sats earned per forwarded payment">Avg Fee Per Route</span>'),
    ],
    'alerts.html': [
        ('Channel skew limit', '<span class="tip" data-tip="Alert when one side of a channel exceeds this % of total capacity. Skewed channels can\'t route in both directions">Channel skew limit</span>'),
        ('Min on-chain balance', '<span class="tip" data-tip="Alert when on-chain balance drops below this amount. You need on-chain sats to open new channels">Min on-chain balance</span>'),
        ('High mempool fee', '<span class="tip" data-tip="Alert when on-chain fees exceed this sat/vB. High fees make channel opens expensive">High mempool fee</span>'),
        ('Min active channels', '<span class="tip" data-tip="Alert if active channel count drops below this number. Zero channels means no routing income">Min active channels</span>'),
    ],
    'mining.html': [
        ('TOTAL HASHRATE', '<span class="tip" data-tip="Combined mining power of your entire fleet in Terahashes per second">TOTAL HASHRATE</span>'),
        ('TOTAL POWER DRAW', '<span class="tip" data-tip="Combined electrical consumption of all miners in Watts">TOTAL POWER DRAW</span>'),
        ('EFFICIENCY', '<span class="tip" data-tip="Joules per Terahash — energy efficiency of your fleet. Lower is better. Sub-20 J/TH is excellent">EFFICIENCY</span>'),
        ('>J/TH<', '><span class="tip" data-tip="Joules per Terahash — energy efficiency rating. Lower = more efficient mining">J/TH</span><'),
        ('>Rating<', '><span class="tip" data-tip="Efficiency rating: Excellent &lt;20 J/TH, Good 20-35 J/TH, Poor &gt;35 J/TH">Rating</span><'),
    ],
}

for filepath in files:
    if not os.path.exists(filepath):
        print(f"Skip (not found): {filepath}")
        continue
    
    fname = os.path.basename(filepath)
    content = open(filepath).read()
    
    # Inject tooltip CSS before </style>
    if '.tip{position:relative' not in content:
        content = content.replace('  </style>', TOOLTIP_CSS + '  </style>', 1)
    
    # Apply page-specific replacements
    if fname in REPLACEMENTS:
        for old, new in REPLACEMENTS[fname]:
            if old and new and old in content:
                content = content.replace(old, new, 1)
    
    open(filepath, 'w').write(content)
    print(f"Updated: {fname}")

print("\nDone! Tooltips injected into all pages.")
