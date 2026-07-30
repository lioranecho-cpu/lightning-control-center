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
  if (!wrap) return;
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

// Auto-init on load
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  buildThemePicker();
});
