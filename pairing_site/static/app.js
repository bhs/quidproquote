// Filtering by official or donor, the highlight toggle, the copy-link button and the button that opens a card's
// detail in place. The cards are rendered on the server; this only hides, marks, copies and shows.
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

  // Opens or closes the detail a card's buttons name in aria-controls. Every button for that detail follows its
  // state, and the page is moved back so the button that was pressed stays where it was on the screen.
  document.addEventListener('click', function (event) {
    var btn = event.target.closest && event.target.closest('.detail-toggle');
    if (!btn) return;
    var detail = document.getElementById(btn.getAttribute('aria-controls'));
    if (!detail) return;
    var before = btn.getBoundingClientRect().top;
    var open = detail.hidden;
    detail.hidden = !open;
    Array.prototype.forEach.call(document.querySelectorAll('.detail-toggle'), function (other) {
      if (other.getAttribute('aria-controls') !== detail.id) return;
      other.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (other.dataset.show) other.textContent = open ? other.dataset.hide : other.dataset.show;
    });
    window.scrollBy(0, btn.getBoundingClientRect().top - before);
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
