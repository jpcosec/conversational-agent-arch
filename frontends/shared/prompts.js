/* Prompts de los agentes (frontends/dev/prompts.html): una tab por agente y
   un panel con encuadre, instruccion estatica y criterios de validacion.
   Datos de /api/system-prompts. */
(function () {
  'use strict';

  var ROLE_LABELS = { conversador: 'Conversador', router: 'Ruteador', orchestrator: 'Orquestador', gate: 'Validación' };
  // Clave del glosario para el tooltip de cada tab (data-tooltip).
  var ROLE_TIPS = { conversador: 'conversador', router: 'ruteador', orchestrator: 'orquestador', gate: 'gate' };

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function roleLabel(role) {
    var span = el('span', null, ROLE_LABELS[role] || role);
    if (ROLE_TIPS[role]) span.setAttribute('data-tooltip', ROLE_TIPS[role]);
    return span;
  }

  function sectionHead(labelNode) {
    var sh = el('div', 'prompts-section-head');
    sh.appendChild(labelNode);
    sh.appendChild(el('span', 'prompts-toggle', '▼'));
    return sh;
  }

  function section(label, content) {
    var div = el('div', 'prompts-section');
    var sh = sectionHead(el('span', null, label));
    var sc = el('div', 'prompts-section-content', content);
    div.appendChild(sh);
    div.appendChild(sc);
    sh.addEventListener('click', function () {
      sh.classList.toggle('collapsed');
      sc.classList.toggle('collapsed');
    });
    return div;
  }

  function criteriaSection(criteria) {
    var div = el('div', 'prompts-section');
    var label = el('span');
    label.appendChild(document.createTextNode('Criterios de '));
    var tip = el('span', null, 'validación');
    tip.setAttribute('data-tooltip', 'gate');
    label.appendChild(tip);
    var sh = sectionHead(label);
    div.appendChild(sh);
    var list = el('ul', 'prompts-criteria');
    criteria.forEach(function (c) {
      var li = el('li', 'prompts-criterion');
      li.appendChild(el('span', 'prompts-criterion-id', c.id || '—'));
      li.appendChild(el('span', 'prompts-criterion-text', c.criterion || ''));
      list.appendChild(li);
    });
    div.appendChild(list);
    sh.addEventListener('click', function () {
      sh.classList.toggle('collapsed');
      list.classList.toggle('collapsed');
    });
    return div;
  }

  function copyAllPrompt(panel) {
    var texts = [];
    panel.querySelectorAll('.prompts-section-content').forEach(function (node) {
      if (!node.classList.contains('collapsed')) texts.push(node.textContent.trim());
    });
    navigator.clipboard.writeText(texts.join('\n\n'));
  }

  function buildPanel(role, a, active) {
    var panel = el('div', 'prompts-panel' + (active ? ' active' : ''));
    panel.dataset.role = role;

    var header = el('div', 'prompts-head');
    var roleNode = el('span', 'prompts-role');
    roleNode.appendChild(roleLabel(role));
    header.appendChild(roleNode);
    if (a.step_count !== undefined) {
      var steps = el('span', 'prompts-meta');
      steps.appendChild(document.createTextNode(a.step_count + ' '));
      var stepWord = el('span', null, 'pasos');
      stepWord.setAttribute('data-tooltip', 'step');
      steps.appendChild(stepWord);
      header.appendChild(steps);
    }
    if (a.criteria) header.appendChild(el('span', 'prompts-meta', a.criteria.length + ' criterios'));
    var copyBtn = el('button', 'btn btn-sm', 'Copiar');
    copyBtn.type = 'button';
    copyBtn.addEventListener('click', function () { copyAllPrompt(panel); });
    header.appendChild(copyBtn);
    panel.appendChild(header);

    if (a.framing) panel.appendChild(section('Encuadre de negocio', a.framing));
    if (a.static_instruction) panel.appendChild(section('Instrucción estática', a.static_instruction));
    if (a.criteria && a.criteria.length) panel.appendChild(criteriaSection(a.criteria));
    return panel;
  }

  function selectTab(tabsEl, panelsEl, role) {
    tabsEl.querySelectorAll('.tab').forEach(function (t) { t.classList.toggle('active', t.dataset.role === role); });
    panelsEl.querySelectorAll('.prompts-panel').forEach(function (p) { p.classList.toggle('active', p.dataset.role === role); });
  }

  async function boot() {
    var tabsEl = document.getElementById('agentTabs');
    var panelsEl = document.getElementById('promptPanels');
    var loading = document.getElementById('loadingState');
    var error = document.getElementById('errorState');

    var data;
    try {
      var res = await fetch('/api/system-prompts');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      data = await res.json();
    } catch (e) {
      loading.classList.add('hidden');
      error.classList.remove('hidden');
      error.textContent = 'Error cargando prompts: ' + e.message;
      return;
    }

    document.getElementById('promptsKbLabel').textContent = 'KB: ' + (data.kb_root || '—');
    var agents = data.agents || {};
    var roles = Object.keys(agents);
    if (!roles.length) {
      loading.className = 'empty-state';
      loading.innerHTML = '<span class="empty-state-icon">🤖</span>No hay agentes configurados en esta KB.';
      return;
    }
    loading.classList.add('hidden');

    roles.forEach(function (role, i) {
      var tab = el('button', 'tab' + (i === 0 ? ' active' : ''));
      tab.type = 'button';
      tab.dataset.role = role;
      tab.appendChild(roleLabel(role));
      tab.addEventListener('click', function () { selectTab(tabsEl, panelsEl, role); });
      tabsEl.appendChild(tab);
      panelsEl.appendChild(buildPanel(role, agents[role], i === 0));
    });
    if (window.initGlossaryTooltips) initGlossaryTooltips();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  if (window.initGlossaryTooltips) initGlossaryTooltips();
  if (window.DemoTour) DemoTour.run();
})();
