#!/usr/bin/env python3
"""
Inject donate QR modal into all LCC pages
Run on ProDesk: python3 ~/lcc/inject_donate.py
"""
import os

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
    '/home/luca/lcc/system.html',
    '/home/luca/lcc/settings.html',
]

MODAL_CSS = '''
  /* ── DONATE MODAL ── */
  .donate-modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:9999;align-items:center;justify-content:center;}
  .donate-modal-overlay.show{display:flex;}
  .donate-modal{background:#161b27;border:1px solid #252d3d;border-radius:16px;padding:28px;max-width:320px;width:90%;text-align:center;position:relative;}
  .donate-modal h3{font-size:16px;font-weight:700;color:#f0f0f0;margin-bottom:4px;}
  .donate-modal p{font-size:12px;color:#888;margin-bottom:20px;}
  .donate-qr{width:200px;height:200px;margin:0 auto 16px;border-radius:8px;background:#fff;padding:8px;}
  .donate-qr img{width:100%;height:100%;}
  .donate-address{background:#0f1117;border:1px solid #252d3d;border-radius:8px;padding:10px 12px;font-family:'JetBrains Mono','Courier New',monospace;font-size:12px;color:#f7931a;margin-bottom:16px;word-break:break-all;}
  .donate-copy-btn{width:100%;background:#f7931a;color:#000;border:none;border-radius:8px;padding:10px;font-family:var(--font);font-size:13px;font-weight:700;cursor:pointer;margin-bottom:10px;}
  .donate-copy-btn:hover{background:#e8851a;}
  .donate-close{background:transparent;border:1px solid #252d3d;color:#888;border-radius:8px;padding:8px 16px;font-family:var(--font);font-size:12px;cursor:pointer;width:100%;}
  .donate-close:hover{border-color:#ef4444;color:#ef4444;}
  .donate-modal-x{position:absolute;top:12px;right:14px;background:none;border:none;color:#888;font-size:18px;cursor:pointer;line-height:1;}
  .donate-modal-x:hover{color:#f0f0f0;}
'''

MODAL_HTML = '''
<!-- Donate Modal -->
<div class="donate-modal-overlay" id="donate-modal" onclick="if(event.target===this)closeDonateModal()">
  <div class="donate-modal">
    <button class="donate-modal-x" onclick="closeDonateModal()">&#10005;</button>
    <h3>&#9889; Support LCC</h3>
    <p>Scan with any Lightning wallet to donate</p>
    <div class="donate-qr">
      <img src="https://api.qrserver.com/v1/create-qr-code/?size=184x184&data=lightning%3Azap%40satslist.shop&bgcolor=ffffff&color=000000&margin=0" alt="Lightning QR" />
    </div>
    <div class="donate-address">zap@satslist.shop</div>
    <button class="donate-copy-btn" onclick="copyDonateAddress()">&#128203; Copy Lightning Address</button>
    <button class="donate-close" onclick="closeDonateModal()">Close</button>
  </div>
</div>
'''

MODAL_JS = '''
  function openDonateModal(){document.getElementById('donate-modal').classList.add('show');}
  function closeDonateModal(){document.getElementById('donate-modal').classList.remove('show');}
  function copyDonateAddress(){
    navigator.clipboard.writeText('zap@satslist.shop').then(()=>{
      const btn=document.querySelector('.donate-copy-btn');
      btn.textContent='\\u2713 Copied!';
      btn.style.background='#22c55e';
      setTimeout(()=>{btn.textContent='\\ud83d\\udccb Copy Lightning Address';btn.style.background='';},2000);
    });
  }
'''

# New donate button that opens modal
OLD_BTN = '<button class="donate-btn" onclick="window.open(\'lightning:zap@satslist.shop\',\'_blank\')">&#9889; Donate 5,000 sats</button>'
NEW_BTN = '<button class="donate-btn" onclick="openDonateModal()">&#9889; Donate 5,000 sats</button>'

# Also handle original no-onclick version
OLD_BTN2 = '<button class="donate-btn">&#9889; Donate 5,000 sats</button>'

for filepath in files:
    if not os.path.exists(filepath):
        print(f"Skip (not found): {filepath}")
        continue

    content = open(filepath).read()

    # Inject CSS
    if 'DONATE MODAL' not in content:
        content = content.replace('  </style>', MODAL_CSS + '\n  </style>', 1)

    # Inject modal HTML before </body>
    if 'donate-modal' not in content:
        content = content.replace('</body>', MODAL_HTML + '\n</body>', 1)

    # Inject JS
    if 'openDonateModal' not in content:
        content = content.replace('function updateTime()', MODAL_JS + '\n  function updateTime()')

    # Update button
    content = content.replace(OLD_BTN, NEW_BTN)
    content = content.replace(OLD_BTN2, NEW_BTN)

    open(filepath, 'w').write(content)
    print(f"Updated: {os.path.basename(filepath)}")

print("\nDone! Donate modal injected into all pages.")
