(function (globalScope) {
  'use strict';

  var HOVER_DELAY_MS = 300;
  var overlayState = {
    root: null,
    timer: null,
    currentAnchor: null
  };

  function getGlossaryEntry(concept) {
    var glossary = globalScope.__glossary || {};
    return glossary[concept] || '';
  }

  function ensureOverlay(documentRef) {
    if (overlayState.root) {
      return overlayState.root;
    }

    var root = documentRef.createElement('div');
    root.setAttribute('data-tooltip-overlay', 'true');
    root.setAttribute('role', 'tooltip');
    root.style.cssText = [
      'position:fixed',
      'display:none',
      'max-width:320px',
      'padding:10px 12px',
      'border-radius:8px',
      'border:1px solid rgba(212,165,116,.18)',
      'background:linear-gradient(180deg, rgba(18,18,26,.98), rgba(10,10,15,.98))',
      'color:#f5f0e8',
      'font:13px/1.45 Inter, sans-serif',
      'box-shadow:0 10px 28px rgba(0,0,0,.35)',
      'pointer-events:none',
      'z-index:10000'
    ].join(';');

    documentRef.body.appendChild(root);
    overlayState.root = root;
    return root;
  }

  function hideTooltip() {
    if (overlayState.timer) {
      clearTimeout(overlayState.timer);
      overlayState.timer = null;
    }
    if (overlayState.root) {
      overlayState.root.style.display = 'none';
      overlayState.root.textContent = '';
    }
    overlayState.currentAnchor = null;
  }

  function placeTooltip(anchor, overlay) {
    var rect = anchor.getBoundingClientRect();
    var margin = 12;
    var top = rect.bottom + margin;
    var left = rect.left;

    overlay.style.left = '0px';
    overlay.style.top = '0px';
    overlay.style.display = 'block';

    var overlayRect = overlay.getBoundingClientRect();
    if (left + overlayRect.width > window.innerWidth - margin) {
      left = window.innerWidth - overlayRect.width - margin;
    }
    if (left < margin) {
      left = margin;
    }
    if (top + overlayRect.height > window.innerHeight - margin) {
      top = rect.top - overlayRect.height - margin;
    }
    if (top < margin) {
      top = margin;
    }

    overlay.style.left = left + 'px';
    overlay.style.top = top + 'px';
  }

  function showTooltip(anchor, concept) {
    if (typeof document === 'undefined') {
      return;
    }

    var text = getGlossaryEntry(concept);
    if (!text) {
      hideTooltip();
      return;
    }

    var overlay = ensureOverlay(document);
    overlay.textContent = text;
    placeTooltip(anchor, overlay);
    overlayState.currentAnchor = anchor;
  }

  function scheduleTooltip(anchor, concept) {
    hideTooltip();
    overlayState.timer = setTimeout(function () {
      showTooltip(anchor, concept);
    }, HOVER_DELAY_MS);
  }

  function attachGlossaryTooltip(element, concept) {
    if (!element || typeof element.addEventListener !== 'function') {
      return function noopCleanup() {};
    }

    var resolvedConcept = concept || element.getAttribute('data-glossary') || element.getAttribute('data-tooltip-concept');
    if (!resolvedConcept) {
      return function noopCleanup() {};
    }

    function onEnter() {
      scheduleTooltip(element, resolvedConcept);
    }

    function onLeave() {
      hideTooltip();
    }

    function onMove() {
      if (overlayState.currentAnchor === element && overlayState.root && overlayState.root.style.display !== 'none') {
        placeTooltip(element, overlayState.root);
      }
    }

    element.addEventListener('mouseenter', onEnter);
    element.addEventListener('focus', onEnter);
    element.addEventListener('mouseleave', onLeave);
    element.addEventListener('blur', onLeave);
    element.addEventListener('mousemove', onMove);

    return function cleanupTooltip() {
      element.removeEventListener('mouseenter', onEnter);
      element.removeEventListener('focus', onEnter);
      element.removeEventListener('mouseleave', onLeave);
      element.removeEventListener('blur', onLeave);
      element.removeEventListener('mousemove', onMove);
      if (overlayState.currentAnchor === element) {
        hideTooltip();
      }
    };
  }

  function initGlossaryTooltips(root) {
    if (typeof document === 'undefined') {
      return [];
    }

    var scope = root || document;
    var elements = scope.querySelectorAll('[data-glossary], [data-tooltip-concept]');
    return Array.prototype.map.call(elements, function (element) {
      return attachGlossaryTooltip(element);
    });
  }

  globalScope.attachGlossaryTooltip = attachGlossaryTooltip;
  globalScope.initGlossaryTooltips = initGlossaryTooltips;
  globalScope.hideGlossaryTooltip = hideTooltip;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      attachGlossaryTooltip: attachGlossaryTooltip,
      initGlossaryTooltips: initGlossaryTooltips,
      hideGlossaryTooltip: hideTooltip
    };
  }
})(typeof window !== 'undefined' ? window : globalThis);
