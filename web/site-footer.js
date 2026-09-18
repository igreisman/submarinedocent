/**
 * SiteFooter — shared page footer for subdocent pages.
 *
 * Usage:
 *   SiteFooter.render();
 *   SiteFooter.render({ onCopy: () => navigator.clipboard.writeText(myUrl()) });
 *
 * Options:
 *   onCopy — optional async fn returning a Promise; if omitted, copies window.location.href
 *
 * Requires site-header.css (which contains the footer styles).
 * Call this before </body>. The function appends the footer at the
 * end of <body>, after whatever content is already there.
 */
const SiteFooter = (() => {
  const COPY = '&copy; subdocent.com';

  function _flashBtn(btn) {
    const orig = btn.dataset.originalText || btn.textContent;
    btn.dataset.originalText = orig;
    btn.textContent = 'Copied';
    btn.classList.add('is-copied');
    setTimeout(() => { btn.textContent = orig; btn.classList.remove('is-copied'); }, 1400);
  }

  function render(options = {}) {
    const { onCopy = null } = options;

    const footer = document.createElement('footer');
    footer.id = 'site-footer';
    footer.innerHTML = `
      <div class="site-footer-copy">
        ${COPY}
        <button class="site-header-copy-btn" id="site-footer-copy-btn" type="button">Copy Link</button>
      </div>
    `;
    document.body.appendChild(footer);

    document.getElementById('site-footer-copy-btn').addEventListener('click', () => {
      const btn = document.getElementById('site-footer-copy-btn');
      const work = onCopy ? onCopy() : navigator.clipboard.writeText(window.location.href);
      Promise.resolve(work).then(() => _flashBtn(btn)).catch(() => {});
    });
  }

  return { render };
})();
