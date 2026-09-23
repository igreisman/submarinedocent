// The video card, shared by the Videos page and the museum pages.
//
// It lives here rather than in each page because of the attribution rule below:
// a rights holder who is also the uploader must appear exactly once, and must
// appear in the row that is never collapsed. Two copies of that rule is one copy
// that can drift, and the drift would quietly hide a credit we are obliged to
// show. The markup is shared; the colours are not, because the Videos page is
// light and the museum pages are dark. Both style the same class names.
(function (global) {
  'use strict';

  const esc = s => String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

  const isSafeUrl = u => /^https?:\/\//i.test(String(u || ''));

  const youtubeId = u => {
    const s = String(u || '');
    const m = s.match(/(?:youtube(?:-nocookie)?\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/i);
    return m ? m[1] : '';
  };

  function thumbnailMarkup(v) {
    const video = v.video || {};
    const explicitThumb = video.thumbnail_url || video.thumb_url || video.poster_url;
    if (isSafeUrl(explicitThumb)) {
      return `<img src="${esc(explicitThumb)}" alt="Thumbnail for ${esc(v.title || 'video')}">`;
    }

    const yid = youtubeId(video.embed_url);
    if (yid) {
      return `<img src="https://img.youtube.com/vi/${esc(yid)}/hqdefault.jpg" alt="Thumbnail for ${esc(v.title || 'video')}">`;
    }

    return `<div class="video-thumb-fallback">Video Preview</div>`;
  }

  function renderPlayer(videoData) {
    if (!videoData) return '';
    if (videoData.kind === 'file') {
      return `<video src="${esc(videoData.embed_url)}" controls preload="metadata" playsinline autoplay title="${esc(videoData.title || 'Video')}"></video>`;
    }
    return `<iframe src="${esc(videoData.embed_url)}" title="${esc(videoData.title || 'Video')}" loading="eager" allow="encrypted-media; picture-in-picture; fullscreen" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>`;
  }

  // Compared case- and space-insensitively, so "Wisconsin Marine Historical
  // Society" and "Wisconsin  Marine  Historical Society" count as one name.
  const normalizeAttribution = s => String(s || '').trim().replace(/\s+/g, ' ').toLowerCase();

  // The channel travels under different keys depending on how old the record
  // is, so both the card and the filter read it through here.
  const channelNameOf = v => {
    const video = v.video || {};
    return (video.channel_name || v.channel_name || video.credit || '').trim();
  };

  // registerPlayable(entry) takes {kind, embed_url, title} and returns the index
  // the page will hand back to its own modal when the thumbnail is clicked.
  function cardHtml(v, registerPlayable) {
    const video = v.video || {};
    if (!isSafeUrl(video.embed_url)) return '';

    const index = registerPlayable({
      kind: video.kind,
      embed_url: video.embed_url,
      title: v.title || 'Video'
    });

    const title = v.title
      ? `<h2 class="video-title">${esc(v.title)}</h2>`
      : '';
    const channelName = channelNameOf(v);
    const channelUrl = (video.channel_url || v.channel_url || video.credit_url || v.video_credit_url || '').trim();
    // A rights holder who is also the uploader would otherwise appear twice on
    // the card: once as the channel, linked to YouTube, and again as the
    // credit, linked wherever they asked us to point. When the two read the
    // same they are collapsed into one, shown here in the channel row and
    // pointing at the credit URL, which is the destination they chose.
    //
    // The surviving line has to be this one, not the credit further down:
    // .video-meta carries is-collapsed on any card with a description, which
    // is every card, and is-collapsed is display:none. Keeping the credit and
    // dropping the channel would hide the attribution behind an expand on a
    // card whose permission is conditional on that attribution being shown.
    const creditText = String(video.credit || '').trim();
    const creditUrl = String(video.credit_url || v.video_credit_url || '').trim();
    const sameAsCredit = Boolean(creditText)
      && normalizeAttribution(channelName) === normalizeAttribution(creditText);
    const attributionUrl = (sameAsCredit && creditUrl) ? creditUrl : channelUrl;
    const channelContent = channelName
      ? (attributionUrl && isSafeUrl(attributionUrl)
        ? `<a href="${esc(attributionUrl)}" target="_blank" rel="noopener noreferrer">${esc(channelName)}</a>`
        : esc(channelName))
      : '';
    const durationText = String(v.duration || '').trim();
    const duration = durationText
      ? `<span class="video-duration" aria-label="Running time ${esc(durationText)}">${esc(durationText)}</span>`
      : '';
    // channelContent, not channelName: a suppressed duplicate must not leave an
    // empty channel row behind, but a duration still earns the row.
    const channel = (channelContent || durationText)
      ? `<div class="video-channel">${channelContent}${duration}</div>`
      : '';
    const descriptionText = (v.description || v.video_description || video.caption || '').trim();
    const description = descriptionText
      ? `<div class="video-description-wrap">
             <p class="video-description is-clamped">${esc(descriptionText)}</p>
             <button type="button" class="video-more" aria-label="Show full description">more ...</button>
           </div>`
      : '';

    // Rendered verbatim. Rights holders dictate exact wording -- Omni Media
    // Services requires "Courtesy warexperience.org. Produced for the Regis
    // University Center for the Study of War Experience" -- and prepending
    // our own "Courtesy of" would corrupt the credit we agreed to give.
    // Suppressed when the channel row above is already showing this exact
    // text and linking to this exact URL. Anything else renders here.
    const creditInner = sameAsCredit
      ? ''
      : (video.credit_url && isSafeUrl(video.credit_url)
        ? `<a href="${esc(video.credit_url)}" target="_blank" rel="noopener noreferrer">${esc(video.credit)}</a>`
        : (video.credit ? esc(video.credit) : ''));
    const rights = v.rights_note
      ? `<div class="video-rights">${esc(v.rights_note)}</div>`
      : '';
    const metaInner = (creditInner || rights)
      ? `${creditInner}${rights}`
      : '';
    const hasDescription = Boolean(descriptionText);
    const meta = metaInner
      ? `<div class="video-meta${hasDescription ? ' is-collapsed' : ''}">${metaInner}</div>`
      : '';

    return `
        <article class="video-card">
          <div class="video-layout">
            <button type="button" class="video-thumb" data-video-index="${index}" aria-label="Play ${esc(v.title || 'video')}">
              ${thumbnailMarkup(v)}
              <span class="video-thumb-play">Play</span>
            </button>
            <div class="video-body">
              ${title}
              ${channel}
              <div class="video-detail-block">
                ${description}${meta}
              </div>
            </div>
          </div>
        </article>`;
  }

  // A "more ..." button is only useful when the text is actually clipped, which
  // is not known until the browser has laid it out.
  function syncDescriptionClamp(root) {
    if (!root) return;
    root.querySelectorAll('.video-description-wrap').forEach(wrap => {
      const description = wrap.querySelector('.video-description');
      const more = wrap.querySelector('.video-more');
      if (!description || !more) return;
      more.hidden = description.scrollHeight <= description.clientHeight + 1;
    });
  }

  global.VideoCard = {
    html: cardHtml,
    player: renderPlayer,
    syncClamp: syncDescriptionClamp,
    channelNameOf,
    thumbnailMarkup,
    youtubeId
  };
})(window);
