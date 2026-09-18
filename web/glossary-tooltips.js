(function () {
  const ENABLE_ATTR = 'data-enable-glossary-tooltips';
  const TERM_CLASS = 'subdoc-glossary-term';
  const TOOLTIP_CLASS = 'subdoc-glossary-tooltip';
  const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'INPUT', 'BUTTON', 'SELECT', 'OPTION', 'CODE', 'PRE']);

  let glossaryEntries = [];
  let glossaryByTerm = new Map();
  let termMatcher = null;
  let tooltip = null;
  let observer = null;
  let hideTooltipTimer = null;
  let activeTarget = null;

  function injectStyles() {
    if (document.getElementById('subdoc-glossary-tooltip-styles')) {
      return;
    }
    const style = document.createElement('style');
    style.id = 'subdoc-glossary-tooltip-styles';
    style.textContent = `
      .${TERM_CLASS} {
        text-decoration-line: underline;
        text-decoration-style: dotted;
        text-decoration-color: rgba(176, 37, 37, 0.88);
        text-decoration-thickness: 1px;
        text-underline-offset: 0.18em;
        cursor: default;
      }

      .${TERM_CLASS}:focus-visible {
        outline: 2px solid rgba(176, 37, 37, 0.28);
        outline-offset: 2px;
        border-radius: 2px;
      }

      .${TOOLTIP_CLASS} {
        position: fixed;
        z-index: 2147483647;
        max-width: min(340px, calc(100vw - 24px));
        padding: 14px 16px;
        border-radius: 14px;
        background: rgba(17, 17, 17, 0.96);
        color: #f5f7fa;
        box-shadow: 0 16px 34px rgba(0, 0, 0, 0.28);
        font-size: 15px;
        line-height: 1.6;
        pointer-events: none;
        opacity: 0;
        transform: translateY(6px);
        transition: opacity 0.12s ease, transform 0.12s ease;
      }

      .${TOOLTIP_CLASS}.is-visible {
        opacity: 1;
        transform: translateY(0);
      }

      .${TOOLTIP_CLASS}::after {
        content: '';
        position: absolute;
        left: 50%;
        bottom: -8px;
        width: 16px;
        height: 16px;
        background: rgba(17, 17, 17, 0.96);
        transform: translateX(-50%) rotate(45deg);
      }

      .${TOOLTIP_CLASS}.is-below::after {
        top: -8px;
        bottom: auto;
      }

      .subdoc-glossary-tooltip-term {
        font-weight: 700;
        margin-bottom: 6px;
        color: #ffffff;
      }

      .subdoc-glossary-tooltip-definition p:first-child {
        margin-top: 0;
      }

      .subdoc-glossary-tooltip-definition p:last-child {
        margin-bottom: 0;
      }

      .subdoc-glossary-tooltip-definition ul,
      .subdoc-glossary-tooltip-definition ol {
        margin: 8px 0 0;
        padding-left: 20px;
      }

      .subdoc-glossary-tooltip-definition a {
        color: #8ec9ff;
      }
    `;
    document.head.appendChild(style);
  }

  function ensureTooltip() {
    if (tooltip) {
      return tooltip;
    }
    tooltip = document.createElement('div');
    tooltip.className = TOOLTIP_CLASS;
    tooltip.setAttribute('role', 'tooltip');
    document.body.appendChild(tooltip);
    return tooltip;
  }

  function decodeHtml(value) {
    const textarea = document.createElement('textarea');
    textarea.innerHTML = value;
    return textarea.value;
  }

  function escapeRegex(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function isWordChar(char) {
    return /[A-Za-z0-9]/.test(char || '');
  }

  function getMatcher(entries) {
    const terms = entries
      .map(entry => entry.term)
      .filter(Boolean)
      .sort((left, right) => right.length - left.length)
      .map(escapeRegex);
    if (!terms.length) {
      return null;
    }
    return new RegExp(terms.join('|'), 'gi');
  }

  function isAnnotatableTextNode(node) {
    if (!node || node.nodeType !== Node.TEXT_NODE) {
      return false;
    }
    if (!node.nodeValue || !node.nodeValue.trim()) {
      return false;
    }
    const parent = node.parentElement;
    if (!parent) {
      return false;
    }
    if (parent.closest(`.${TERM_CLASS}, .${TOOLTIP_CLASS}`)) {
      return false;
    }
    if (SKIP_TAGS.has(parent.tagName)) {
      return false;
    }
    if (parent.isContentEditable || parent.closest('[contenteditable="true"]')) {
      return false;
    }
    return true;
  }

  function replaceTextNode(node) {
    if (!termMatcher || !isAnnotatableTextNode(node)) {
      return;
    }

    const text = node.nodeValue;
    let match;
    let lastIndex = 0;
    let fragment = null;
    termMatcher.lastIndex = 0;

    while ((match = termMatcher.exec(text))) {
      const start = match.index;
      const value = match[0];
      const end = start + value.length;
      const before = start > 0 ? text[start - 1] : '';
      const after = end < text.length ? text[end] : '';
      if (isWordChar(before) || isWordChar(after)) {
        continue;
      }

      const entry = glossaryByTerm.get(value.toLowerCase());
      if (!entry) {
        continue;
      }

      if (!fragment) {
        fragment = document.createDocumentFragment();
      }

      if (start > lastIndex) {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex, start)));
      }

      const span = document.createElement('span');
      span.className = TERM_CLASS;
      span.tabIndex = 0;
      span.dataset.glossaryTerm = entry.term;
      span.textContent = text.slice(start, end);
      fragment.appendChild(span);
      lastIndex = end;
    }

    if (!fragment) {
      return;
    }

    if (lastIndex < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
    }

    node.parentNode.replaceChild(fragment, node);
  }

  function annotate(root) {
    if (!root || !termMatcher) {
      return;
    }
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        return isAnnotatableTextNode(node) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    const nodes = [];
    while (walker.nextNode()) {
      nodes.push(walker.currentNode);
    }
    nodes.forEach(replaceTextNode);
  }

  function getEntryForTarget(target) {
    if (!target) {
      return null;
    }
    return glossaryByTerm.get(String(target.dataset.glossaryTerm || '').toLowerCase()) || null;
  }

  function positionTooltip(target, node) {
    const rect = target.getBoundingClientRect();
    const tooltipRect = node.getBoundingClientRect();
    const gap = 14;
    let top = rect.top - tooltipRect.height - gap;
    let placeBelow = false;

    if (top < 10) {
      top = rect.bottom + gap;
      placeBelow = true;
    }

    let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
    left = Math.max(12, Math.min(left, window.innerWidth - tooltipRect.width - 12));

    node.style.left = `${left}px`;
    node.style.top = `${top}px`;
    node.classList.toggle('is-below', placeBelow);
  }

  function showTooltip(target) {
    const entry = getEntryForTarget(target);
    if (!entry) {
      return;
    }
    const node = ensureTooltip();
    if (hideTooltipTimer) {
      window.clearTimeout(hideTooltipTimer);
      hideTooltipTimer = null;
    }
    activeTarget = target;
    node.innerHTML = `
      <div class="subdoc-glossary-tooltip-term">${entry.term}</div>
      <div class="subdoc-glossary-tooltip-definition">${entry.definition || ''}</div>
    `;
    node.classList.add('is-visible');
    positionTooltip(target, node);
  }

  function hideTooltip() {
    if (!tooltip) {
      return;
    }
    activeTarget = null;
    tooltip.classList.remove('is-visible', 'is-below');
  }

  function queueHideTooltip() {
    if (hideTooltipTimer) {
      window.clearTimeout(hideTooltipTimer);
    }
    hideTooltipTimer = window.setTimeout(hideTooltip, 80);
  }

  function onPointerOver(event) {
    const target = event.target.closest(`.${TERM_CLASS}`);
    if (!target) {
      return;
    }
    showTooltip(target);
  }

  function onPointerOut(event) {
    const target = event.target.closest(`.${TERM_CLASS}`);
    if (!target) {
      return;
    }
    queueHideTooltip();
  }

  function onFocusIn(event) {
    const target = event.target.closest(`.${TERM_CLASS}`);
    if (!target) {
      return;
    }
    showTooltip(target);
  }

  function onFocusOut(event) {
    const target = event.target.closest(`.${TERM_CLASS}`);
    if (!target) {
      return;
    }
    queueHideTooltip();
  }

  function onViewportChange() {
    if (activeTarget && tooltip && tooltip.classList.contains('is-visible')) {
      positionTooltip(activeTarget, tooltip);
    }
  }

  async function loadGlossary() {
    const response = await fetch('/api/glossary');
    if (!response.ok) {
      throw new Error(`Failed to load glossary: HTTP ${response.status}`);
    }
    glossaryEntries = await response.json();
    glossaryByTerm = new Map(
      glossaryEntries
        .filter(entry => entry && entry.term)
        .map(entry => [String(entry.term).toLowerCase(), entry])
    );
    termMatcher = getMatcher(glossaryEntries);
  }

  function observe(root) {
    if (observer) {
      observer.disconnect();
    }
    observer = new MutationObserver(mutations => {
      mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === Node.TEXT_NODE) {
            replaceTextNode(node);
            return;
          }
          if (node.nodeType === Node.ELEMENT_NODE) {
            annotate(node);
          }
        });
      });
    });
    observer.observe(root, { childList: true, subtree: true });
  }

  async function init(options = {}) {
    const root = options.root || document.body;
    if (!root || !document.body || !document.querySelector(`[${ENABLE_ATTR}]`)) {
      return;
    }

    injectStyles();
    await loadGlossary();
    annotate(root);
    observe(root);

    document.addEventListener('mouseover', onPointerOver);
    document.addEventListener('mouseout', onPointerOut);
    document.addEventListener('focusin', onFocusIn);
    document.addEventListener('focusout', onFocusOut);
    window.addEventListener('scroll', onViewportChange, true);
    window.addEventListener('resize', onViewportChange);
  }

  window.SubDocGlossaryTooltips = {
    init,
    refresh(root = document.body) {
      annotate(root);
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      init().catch(() => { });
    }, { once: true });
  } else {
    init().catch(() => { });
  }
})();
