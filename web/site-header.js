/**
 * SiteHeader — shared page header for subdocent pages.
 *
 * Usage:
 *   SiteHeader.render({
 *     title:    'Submarine Museums',          // hero h1
 *     subtitle: 'Preserved submarines…',     // hero subtitle paragraph
 *     feedback: 'Know of a museum to add?',  // optional custom feedback prompt (sentence before the link)
 *   });
 *
 * Call this before </body>. The function inserts the disclaimer, nav, and
 * hero at the top of <body>, before whatever content is already there.
 */
const SiteHeader = (() => {
  const BRAND_HREF  = '/web/faqs.html';
  const BRAND_TEXT  = 'Home';
  const ABOUT_HREF  = '/welcome.html?force=1';
  const FEEDBACK_HREF = '/web/contact.html';
  const DEFAULT_FEEDBACK = 'Can\'t find what you\'re looking for? Have corrections or suggestions?';
  const WARNING_TEXT = '<strong>Work in progress:</strong> this site is still being developed, and some content and historical data remain unverified.';

  function render(options = {}) {
    const {
      title    = '',
      subtitle = '',
      feedback = DEFAULT_FEEDBACK,
    } = options;

    const html = `
      <div class="site-warning">${WARNING_TEXT}</div>
      <nav id="topnav">
        <a class="topnav-brand" href="${BRAND_HREF}">${BRAND_TEXT}</a>
        <div class="topnav-links">
          <a href="${ABOUT_HREF}">About</a>
        </div>
      </nav>
      <div id="site-hero">
        <h1>${title}</h1>
        ${subtitle ? `<p class="site-hero-subtitle">${subtitle}</p>` : ''}
        <div class="site-feedback-banner">
          💡 <strong>Help us improve!</strong> ${feedback}
          <a href="${FEEDBACK_HREF}">Share your feedback</a> to help us make this resource better.
        </div>
      </div>
    `;

    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    document.body.insertBefore(wrapper, document.body.firstChild);
  }

  return { render };
})();
