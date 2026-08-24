const LCC_THEMES = {
  midnight: {
    name: '🌊 Midnight',
    '--bg': '#0f1117',
    '--surface': '#161b27',
    '--surface2': '#1c2233',
    '--border': '#252d3d',
    '--text': '#e2e8f0',
    '--muted': '#4a5568',
  },
  obsidian: {
    name: '🌑 Obsidian',
    '--bg': '#0a0a0a',
    '--surface': '#111111',
    '--surface2': '#181818',
    '--border': '#222222',
    '--text': '#f0f0f0',
    '--muted': '#555555',
  },
  amber: {
    name: '🟠 Amber',
    '--bg': '#0d0900',
    '--surface': '#1a1200',
    '--surface2': '#241a00',
    '--border': '#3d2e00',
    '--text': '#fdf0d5',
    '--muted': '#8a6d3b',
  },
  forest: {
    name: '🌲 Forest',
    '--bg': '#0a0f0a',
    '--surface': '#111a11',
    '--surface2': '#162016',
    '--border': '#1e2e1e',
    '--text': '#d4edda',
    '--muted': '#4a7c59',
  },
};

function applyTheme(name) {
  const theme = LCC_THEMES[name];
  if (!theme) return;
  const root = document.documentElement;
  Object.entries(theme).forEach(([k, v]) => {
    if (k !== 'name') root.style.setProperty(k, v);
  });
  localStorage.setItem('lcc-theme', name);
  // Update active state on buttons if picker exists
  document.querySelectorAll('.theme-btn').forEach(btn => {
    const isActive = btn.dataset.theme === name;
    btn.classList.toggle('active', isActive);
    btn.style.borderColor = isActive ? '#f7931a' : 'var(--border)';
    btn.style.color = isActive ? '#f7931a' : 'var(--text)';
  });
}

function initTheme() {
  const saved = localStorage.getItem('lcc-theme') || 'midnight';
  applyTheme(saved);
}

function buildThemePicker() {
  const wrap = document.getElementById('lcc-theme-picker');
  if (!wrap) { setTimeout(buildThemePicker, 150); return; }
  wrap.innerHTML = Object.entries(LCC_THEMES).map(([key, t]) => `
    <button class="theme-btn" data-theme="${key}" onclick="applyTheme('${key}')"
      style="flex:1;padding:5px 4px;border-radius:6px;border:1px solid var(--border);
             background:var(--surface2);color:var(--text);cursor:pointer;font-size:10px;
             font-family:inherit;transition:all .15s;">
      ${t.name}
    </button>
  `).join('');
  // Mark active
  const current = localStorage.getItem('lcc-theme') || 'midnight';
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.theme === current);
    if (btn.dataset.theme === current) {
      btn.style.borderColor = 'var(--orange)';
      btn.style.color = 'var(--orange)';
    }
  });
}

// Mobile responsive CSS — injected on every page
function injectMobileNav() {
  if(window.innerWidth > 768) return;
  // Add floating hamburger button
  const btn = document.createElement('div');
  btn.innerHTML = '☰';
  btn.style.cssText = 'position:fixed;top:12px;left:12px;z-index:1001;background:var(--orange);border:none;border-radius:10px;padding:10px 16px;font-size:22px;cursor:pointer;color:#000;box-shadow:0 4px 16px rgba(247,147,26,.4);font-weight:bold;';
  btn.onclick = () => {
    const sb = document.querySelector('.sidebar');
    if(sb) sb.classList.toggle('show');
  };
  document.body.appendChild(btn);
  // Close sidebar when clicking a nav item
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const sb = document.querySelector('.sidebar');
      if(sb) sb.classList.remove('show');
    });
  });
  // Close sidebar overlay
  const overlay = document.createElement('div');
  overlay.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:998;';
  overlay.onclick = () => {
    document.querySelector('.sidebar').classList.remove('show');
    overlay.style.display = 'none';
  };
  document.body.appendChild(overlay);
  // Watch for sidebar show/hide
  const observer = new MutationObserver(() => {
    const sb = document.querySelector('.sidebar');
    overlay.style.display = sb && sb.classList.contains('show') ? 'block' : 'none';
  });
  const sb = document.querySelector('.sidebar');
  if(sb) observer.observe(sb, {attributes: true, attributeFilter: ['class']});
}

function injectMobileCSS() {
  const style = document.createElement('style');
  style.textContent = `
    @media (max-width: 768px) {
      /* Hide sidebar completely on mobile */
      .sidebar { 
        display: none !important; 
        width: 0 !important;
      }
      .sidebar.show { 
        display: flex !important; 
        position: fixed; 
        z-index: 999; 
        width: 220px !important; 
        top: 0; left: 0; bottom: 0;
        box-shadow: 4px 0 20px rgba(0,0,0,.5);
      }
      /* Main content fills full width */
      .main, .main-content { 
        margin-left: 0 !important; 
        padding: 10px !important; 
        width: 100vw !important;
        max-width: 100vw !important;
        box-sizing: border-box !important;
      }
      /* Top bar full width */
      .topbar { 
        margin-left: 0 !important; 
        padding: 8px 10px !important; 
        width: 100% !important;
      }
      /* Status bar full width */
      .statusbar { 
        margin-left: 0 !important; 
        font-size: 9px !important; 
        flex-wrap: wrap !important; 
        left: 0 !important;
        width: 100% !important;
      }
      /* Stack all grids vertically */
      .summary-grid, .charts-grid, .bottom-row, 
      .wallet-cards, .wallet-grid, .system-grid,
      .mining-grid, .miner-grid { 
        grid-template-columns: 1fr !important; 
      }
      /* Cards full width */
      .summary-card, .channel-card, .panel { 
        min-width: unset !important; 
        width: 100% !important;
        overflow-x: auto !important;
      }
      /* Smaller text on mobile */
      .ch-actions { flex-wrap: wrap !important; gap: 4px !important; }
      .action-btn { font-size: 9px !important; padding: 3px 6px !important; }
      .balance-bar-labels { font-size: 10px !important; }
      .ch-stats { flex-wrap: wrap !important; gap: 4px !important; }
      .ch-stat { font-size: 10px !important; }
      .pairs-table { font-size: 10px !important; }
      .tx-table { font-size: 10px !important; }
      .projection-card { font-size: 11px !important; }
      .tab { font-size: 10px !important; padding: 5px 8px !important; }
      .sb-item { min-width: unset !important; }
      /* Page title truncation fix */
      h2, .page-title { font-size: 18px !important; }
      .page-subtitle { font-size: 11px !important; }
      /* Hamburger always visible */
      .hamburger { display: flex !important; }
      /* Prevent horizontal scroll */
      body, html { overflow-x: hidden !important; max-width: 100vw !important; }
      /* Channel sort dropdown */
      .channel-list { gap: 8px !important; }
      /* Hide less important elements on mobile */
      .donate-modal-trigger, .donate-btn { display: none !important; }
      .community-badge { display: none !important; }
      /* Summary cards - stack single column */
      .summary-grid { grid-template-columns: repeat(2, 1fr) !important; gap: 8px !important; }
      .summary-card { padding: 12px !important; }
      /* Charts side by side is ok but stack if needed */
      .charts-grid { grid-template-columns: 1fr !important; gap: 8px !important; }
      /* Mining cards stack vertically */
      .miner-cards, .miner-grid { grid-template-columns: 1fr !important; }
      /* Hide pool status, fleet efficiency, and mining summary on mobile */
      #pool-status-panel, #fleet-efficiency-panel, #mining-summary-grid { display: none !important; }
      /* Node health compact */
      .node-health { font-size: 11px !important; }
      /* Topbar compact */
      .topbar-right { font-size: 10px !important; }
      .topbar-sats { font-size: 13px !important; }
      /* Two column bottom row */
      .bottom-row { grid-template-columns: 1fr !important; }
      /* System page grids */
      .system-grid { grid-template-columns: 1fr !important; }
      /* Fee policy and forwarding side by side → stack */
      .routing-grid { grid-template-columns: 1fr !important; }
      /* Wallet cards stack */
      .wallet-row { flex-direction: column !important; }
      /* Hide theme picker on mobile — save sidebar space */
      .theme-picker, .sidebar-footer .theme-btn, #theme-picker-container { display: none !important; }
      .sidebar-footer { padding: 8px 14px !important; }
    }
  `;
  document.head.appendChild(style);
}

// Auto-init on load
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  buildThemePicker();
  injectMobileCSS();
  injectMobileNav();
  // Show landscape hint on mobile portrait
  if(window.innerWidth <= 768 && window.innerHeight > window.innerWidth && !sessionStorage.getItem('lcc_landscape_hint')) {
    const hint = document.createElement('div');
    hint.style.cssText = 'position:fixed;bottom:60px;left:50%;transform:translateX(-50%);z-index:1002;background:var(--orange);color:#000;padding:12px 20px;border-radius:10px;font-size:13px;font-weight:600;font-family:system-ui;box-shadow:0 4px 16px rgba(0,0,0,.3);text-align:center;max-width:90%;';
    hint.innerHTML = '📱 Rotate your device for the best LCC experience <div style="font-size:11px;margin-top:6px;opacity:.7;">Tap to dismiss</div>';
    hint.onclick = () => { hint.remove(); sessionStorage.setItem('lcc_landscape_hint', '1'); };
    document.body.appendChild(hint);
    setTimeout(() => hint.remove(), 8000);
  }
});
