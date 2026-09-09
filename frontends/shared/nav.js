/* Topbar común a todas las vistas: una sola fuente de verdad.
 *
 * Cada página importa theme.css + nav.js y pone <div id="appNavMount"></div>
 * donde quiera la topbar. Este script inyecta TODO el HTML: brand, nav links,
 * chips de KB/health, logos. El CSS ya vive en theme.css.
 *
 * Grupos: Chat (producto) · Operación (leads, métricas) · Desarrollo
 * (inspector, flujo, KB, dev). Los separadores los dibuja theme.css
 * (.app-nav a[data-group-start]::before y [data-group-label]::after).
 */
(function () {
  var LINKS = [
    { testid: 'nav-chat',      group: 'chat',       href: '/chat',   label: 'Chat' },
    { testid: 'nav-leads',     group: 'operacion',   href: '/leads',   label: 'Leads' },
    { testid: 'nav-dashboard', group: 'operacion',   href: '/dashboard', label: 'Métricas' },
    { testid: 'nav-inspector', group: 'desarrollo',  href: '/',         label: 'Inspector' },
    { testid: 'nav-flow',      group: 'desarrollo',  href: '/flow',     label: 'Flujo' },
    { testid: 'nav-mindmap',   group: 'desarrollo',  href: '/mindmap',  label: 'KB' },
    { testid: 'nav-profiles',  group: 'desarrollo',  href: '/users',    label: 'Perfiles' },
    { testid: 'nav-prompts',   group: 'desarrollo',  href: '/dev/prompts',label: 'Prompts' },
    { testid: 'nav-dev',       group: 'desarrollo',  href: '/dev',       label: 'Dev' }
  ];

  function injectTopbar() {
    var mount = document.getElementById('appNavMount');
    if (!mount || mount.dataset._navInjected) return;
    mount.dataset._navInjected = '1';

    var header = document.createElement('header');
    header.className = 'app-topbar';
    header.setAttribute('data-testid', 'nav-topbar');

    header.innerHTML = [
      '<a class="app-topbar-brand" data-testid="nav-brand" href="/" id="appBrand">Agente</a>',
      '<nav class="app-nav" id="appNav">',
      LINKS.map(function (l) {
        return '<a data-testid="' + l.testid + '" data-nav-group="' + l.group + '" href="' + l.href + '">' + l.label + '</a>';
      }).join(''),
      '</nav>',
      '<div class="app-topbar-meta">',
      '<span class="app-topbar-chip" id="kbLabel">KB</span>',
      '<span class="app-topbar-chip" id="healthLabel">—</span>',
      '</div>'
    ].join('');

    mount.appendChild(header);
  }

  function markActive() {
    var path = location.pathname.replace(/\/$/, '') || '/';
    document.querySelectorAll('#appNav a').forEach(function (a) {
      var href = a.getAttribute('href').replace(/\/$/, '') || '/';
      a.classList.toggle('active', href === path);
      a.toggleAttribute('data-active', href === path);
    });
  }

  function markGroups() {
    var seen = {};
    document.querySelectorAll('#appNav a').forEach(function (a) {
      var g = a.getAttribute('data-nav-group');
      if (!g || seen[g]) return;
      seen[g] = true;
      a.setAttribute('data-group-start', 'true');
      a.setAttribute('data-group-label', GROUPS[g] || '');
    });
  }

  var GROUPS = { chat: 'Chat', operacion: 'Operación', desarrollo: 'Desarrollo' };

  function applyConfig(cfg, health) {
    var brand = document.getElementById('appBrand');
    var kb = document.getElementById('kbLabel');
    var hl = document.getElementById('healthLabel');
    if (brand) brand.textContent = cfg.name || cfg.runtime_title || 'Agente';
    if (kb) kb.textContent = cfg.kb_label || cfg.name || 'KB';
    if (hl) hl.textContent = health.status || 'unknown';
    var input = document.querySelector('[data-testid="chat-input"]');
    if (input && cfg.input_placeholder) input.placeholder = cfg.input_placeholder;
  }

  // Logos
  var LOGOS = {
    brand: {
      src: 'https://pharma.heyantonia.com/_next/image?url=%2Fbrand%2Fantonia-lockup-2027.png&w=384&q=75',
      alt: 'Antonia', testid: 'topbar-logo-brand'
    },
    client: {
      src: 'https://www.laboratoriochile.cl/wp-content/themes/teva-lab/assets/img/logo-teva-v2.svg',
      alt: 'Teva · Laboratorio Chile', testid: 'topbar-logo-client'
    }
  };

  function makeLogo(spec) {
    var img = document.createElement('img');
    img.className = 'app-topbar-logo';
    img.src = spec.src;
    img.alt = spec.alt;
    img.setAttribute('data-testid', spec.testid);
    img.addEventListener('error', function () { img.remove(); });
    return img;
  }

  function mountLogos() {
    var bar = document.querySelector('.app-topbar');
    if (!bar || bar.querySelector('.app-topbar-logo')) return;
    var brand = document.getElementById('appBrand');
    if (brand) bar.insertBefore(makeLogo(LOGOS.brand), brand);
    var meta = bar.querySelector('.app-topbar-meta');
    if (meta) meta.appendChild(makeLogo(LOGOS.client));
    else bar.appendChild(makeLogo(LOGOS.client));
  }

  function boot() {
    injectTopbar();
    mountLogos();
    markActive();
    markGroups();
    Promise.all([
      fetch('/api/config').then(function (r) { return r.json() }).catch(function () { return {} }),
      fetch('/api/health').then(function (r) { return r.json() }).catch(function () { return {} })
    ]).then(function (res) { applyConfig(res[0] || {}, res[1] || {}) });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();