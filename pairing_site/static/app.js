// Filtering by official or donor, the highlight toggle and the copy-link button. The cards are rendered on the
// server; this only hides, marks and copies.
(function () {
  function cards() { return Array.prototype.slice.call(document.querySelectorAll('#cards .card')); }

  function applyFilters() {
    var official = (document.getElementById('filter-official') || {}).value || '';
    var donor = (document.getElementById('filter-donor') || {}).value || '';
    var shown = 0;
    cards().forEach(function (card) {
      var ok = (!official || card.dataset.official === official) && (!donor || card.dataset.donor === donor);
      card.hidden = !ok;
      if (ok) shown += 1;
    });
    var count = document.getElementById('shown-count');
    if (count) count.textContent = shown + ' card' + (shown === 1 ? '' : 's') + ' shown';
    var none = document.getElementById('no-match');
    if (none) none.hidden = shown !== 0 || cards().length === 0;
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var box = document.createElement('textarea');
      box.value = text;
      box.style.position = 'fixed';
      box.style.opacity = '0';
      document.body.appendChild(box);
      box.select();
      try { document.execCommand('copy') ? resolve() : reject(new Error('copy refused')); }
      catch (err) { reject(err); }
      finally { document.body.removeChild(box); }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    ['filter-official', 'filter-donor'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('change', applyFilters);
    });
    var toggle = document.getElementById('toggle-highlight');
    if (toggle) toggle.addEventListener('click', function () {
      var off = document.body.classList.toggle('hl-off');
      toggle.setAttribute('aria-pressed', off ? 'false' : 'true');
      toggle.textContent = 'Highlight shared words: ' + (off ? 'off' : 'on');
    });
  });

  document.addEventListener('click', function (event) {
    var btn = event.target.closest && event.target.closest('.copy-link');
    if (!btn) return;
    var url = window.location.origin + btn.dataset.path;
    copyText(url).then(function () { btn.textContent = 'Copied'; }, function () { btn.textContent = url; });
    setTimeout(function () { if (btn.textContent === 'Copied') btn.textContent = 'Copy link'; }, 2000);
  });
})();

// Each card is closed: tapping a confidence chip shows or hides its reason, and "Show detail" fetches the card's
// detail section (htmx does the request; a plain fetch stands in when the htmx script did not load) and shows or
// hides it. A failed fetch says so and the next tap tries again.
(function () {
  function setOpen(btn, open) {
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    var target = document.getElementById(btn.getAttribute('aria-controls'));
    if (target) target.hidden = !open;
    return target;
  }

  function loadDetail(btn, panel) {
    panel.setAttribute('aria-busy', 'true');
    panel.textContent = 'Loading the detail\u2026';
    if (window.htmx) { window.htmx.trigger(btn, 'show-detail'); return; }
    fetch(btn.getAttribute('hx-get'), { headers: { 'HX-Request': 'true' } }).then(function (res) {
      if (!res.ok) throw new Error(res.status);
      return res.text();
    }).then(function (html) {
      panel.innerHTML = html;
      panel.dataset.loaded = 'true';
      panel.removeAttribute('aria-busy');
    }, function () { failed(panel); });
  }

  function failed(panel) {
    panel.textContent = 'The detail could not be loaded. Tap Hide detail, then Show detail, to try again.';
    panel.removeAttribute('aria-busy');
  }

  document.addEventListener('click', function (event) {
    var target = event.target.closest && event.target.closest('.chip-btn, .detail-toggle');
    if (!target) return;
    var open = target.getAttribute('aria-expanded') !== 'true';
    var panel = setOpen(target, open);
    if (!target.classList.contains('detail-toggle')) return;
    target.textContent = open ? 'Hide detail' : 'Show detail';
    if (open && panel && panel.dataset.loaded !== 'true') loadDetail(target, panel);
  });

  document.addEventListener('htmx:afterSwap', function (event) {
    var panel = event.target;
    if (panel.classList && panel.classList.contains('detail')) {
      panel.dataset.loaded = 'true';
      panel.removeAttribute('aria-busy');
    }
  });
  ['htmx:responseError', 'htmx:sendError'].forEach(function (name) {
    document.addEventListener(name, function (event) {
      var panel = event.detail && event.detail.target;
      if (panel && panel.classList && panel.classList.contains('detail')) failed(panel);
    });
  });
})();

// The priority form: the outlet and whose-words fields belong to a news report only.
(function () {
  var type = document.getElementById('source-type');
  var news = document.getElementById('news-fields');
  if (!type || !news) return;
  function sync() { news.hidden = type.value !== 'news report'; }
  type.addEventListener('change', sync);
  sync();
})();
