/**
 * AdminEnvBanner — a sticky banner that makes it obvious whether an admin
 * editor page is talking to LOCAL or PRODUCTION.
 *
 * The editors save via a relative API base (`const API = ''`), so they write to
 * whichever origin served the page. It is easy to think you are editing locally
 * while actually editing the live site (a stray bookmark or history entry to the
 * production URL). This banner removes that ambiguity.
 *
 * Usage: drop `<script src="/web/admin-env-banner.js"></script>` anywhere in an
 * admin page. It self-injects on load — no function call needed.
 */
(() => {
  const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '0.0.0.0', '::1']);
  const host = location.hostname;
  const isLocal = LOCAL_HOSTS.has(host) || host.endsWith('.local');

  const banner = document.createElement('div');
  banner.id = 'admin-env-banner';
  banner.textContent = isLocal
    ? `LOCAL DEV — editing your machine (${host || 'localhost'}). Safe to test.`
    : `⚠ PRODUCTION — editing the LIVE site (${host}). Changes are visible to visitors.`;
  Object.assign(banner.style, {
    position: 'sticky',
    top: '0',
    zIndex: '2147483647',
    padding: '8px 16px',
    font: '600 14px/1.4 system-ui, -apple-system, Segoe UI, sans-serif',
    textAlign: 'center',
    color: '#fff',
    letterSpacing: '0.02em',
    background: isLocal ? '#1f7a3d' : '#b91c1c',
    boxShadow: '0 1px 4px rgba(0,0,0,0.25)',
  });

  const mount = () => {
    if (document.getElementById('admin-env-banner') !== banner && document.body) {
      document.body.insertBefore(banner, document.body.firstChild);
    }
  };

  if (document.body) {
    mount();
  } else {
    document.addEventListener('DOMContentLoaded', mount);
  }
})();
