#!/usr/bin/env python3
"""
Inject mobile responsive CSS + hamburger menu into all LCC pages
Run on ProDesk: python3 ~/lcc/inject_mobile.py
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
]

MOBILE_CSS = '''
  /* ── HAMBURGER (hidden on desktop) ── */
  .hamburger { display: none; }

  /* ── MOBILE RESPONSIVE ── */
  @media (max-width: 768px) {
    .sidebar { transform: translateX(-220px); transition: transform .25s ease; z-index:200; }
    .sidebar.open { transform: translateX(0); }
    .sidebar-overlay { display:none; position:fixed; inset:0; background:rgba(0,0,0,.6); z-index:199; }
    .sidebar-overlay.show { display:block; }
    .main { margin-left: 0 !important; }
    .topbar { padding: 10px 16px; height:auto; min-height:54px; flex-wrap:wrap; gap:8px; }
    .topbar-left p { display: none; }
    .topbar-left h1 { font-size: 13px; }
    .topbar-right { gap:10px; flex-wrap:wrap; font-size:11px; }
    .balance-display .sats { font-size:13px; }
    .hamburger { display:flex !important; align-items:center; justify-content:center; width:36px; height:36px; background:var(--surface2); border:1px solid var(--border); border-radius:8px; cursor:pointer; color:var(--text); font-size:18px; flex-shrink:0; margin-right:8px; }
    .content { padding: 16px; }
    .stat-grid, .summary-grid, .alert-summary { grid-template-columns: repeat(2,1fr) !important; gap:10px !important; }
    .charts-row, .two-col, .bottom-row, .charts-grid, .alerts-layout, .journal-layout { grid-template-columns: 1fr !important; gap:12px !important; }
    .miners-grid { grid-template-columns: 1fr !important; }
    .ch-table, .peers-table, .eff-table, .fwd-table, .pairs-table, .tx-table { display:block; overflow-x:auto; white-space:nowrap; }
    .page-header { flex-direction:column; gap:12px; align-items:flex-start !important; }
    .time-filters { flex-wrap:wrap; }
    .statusbar { flex-wrap:wrap; gap:12px; padding:10px 16px; }
    .statusbar .sb-item:last-child { margin-left:0 !important; }
    .login-wrap { padding:16px; }
    .login-card { padding:20px; }
    .tip::after { bottom:auto !important; top:calc(100% + 8px) !important; left:0 !important; transform:none !important; width:180px !important; }
    .stat-value { font-size:15px !important; }
    .sc-value { font-size:18px !important; }
    .balance-grid { grid-template-columns: 1fr !important; }
    .connect-form { flex-direction:column !important; }
  }
  @media (max-width: 480px) {
    .stat-grid, .summary-grid, .alert-summary { grid-template-columns: 1fr !important; }
  }
'''

MOBILE_JS = '''
  // ── Mobile sidebar toggle ──
  function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('show');
  }
  document.addEventListener('DOMContentLoaded', function() {
    // Add overlay div if not present
    if (!document.querySelector('.sidebar-overlay')) {
      const overlay = document.createElement('div');
      overlay.className = 'sidebar-overlay';
      overlay.onclick = toggleSidebar;
      document.body.appendChild(overlay);
    }
    // Close sidebar when nav item clicked on mobile
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', function() {
        if(window.innerWidth <= 768) {
          document.querySelector('.sidebar').classList.remove('open');
          document.querySelector('.sidebar-overlay').classList.remove('show');
        }
      });
    });
  });
'''

HAMBURGER_HTML = '<button class="hamburger" onclick="toggleSidebar()">&#9776;</button>'

for filepath in files:
    if not os.path.exists(filepath):
        print(f"Skip (not found): {filepath}")
        continue

    content = open(filepath).read()

    # Inject mobile CSS before </style>
    if 'MOBILE RESPONSIVE' not in content:
        content = content.replace('  </style>', MOBILE_CSS + '\n  </style>', 1)

    # Inject mobile JS before </script> (last one)
    if 'toggleSidebar' not in content:
        # Find the last </script> and inject before it
        last_script = content.rfind('</script>')
        if last_script != -1:
            content = content[:last_script] + MOBILE_JS + content[last_script:]

    # Add hamburger button to topbar-left
    if 'hamburger' not in content:
        content = content.replace(
            '<div class="topbar-left">',
            HAMBURGER_HTML + '\n    <div class="topbar-left">'
        )

    open(filepath, 'w').write(content)
    print(f"Updated: {os.path.basename(filepath)}")

print("\nDone! Mobile responsive injected into all pages.")
print("Test at: https://lcc.satslist.shop/dashboard (resize browser or use mobile)")
