/* Snapshot age, computed in the browser from an embedded ISO timestamp.
 *
 * This is the ONE staleness mechanism that does not depend on CI. GitHub disables
 * `schedule:` triggers after 60 days of repository inactivity -- precisely the situation
 * where a staleness warning matters most -- so a site nobody has rebuilt in a year still
 * tells the reader so, because the arithmetic happens on their machine at read time.
 */
(function () {
  var DAY = 86400000;
  document.querySelectorAll('[data-generated-utc]').forEach(function (el) {
    var iso = el.getAttribute('data-generated-utc');
    var then = Date.parse(iso);
    if (isNaN(then)) return;
    var days = Math.floor((Date.now() - then) / DAY);
    var band = days < 90 ? 'fresh' : days < 180 ? 'ageing' : days < 365 ? 'stale' : 'abandoned';
    el.setAttribute('data-age-band', band);
    var out = el.querySelector('[data-age-text]');
    if (out) {
      out.textContent = days < 1 ? 'today'
        : days === 1 ? '1 day old'
        : days < 60 ? days + ' days old'
        : Math.round(days / 30.44) + ' months old';
    }
    var warn = document.querySelector('[data-age-warning]');
    if (warn && (band === 'stale' || band === 'abandoned')) {
      warn.classList.remove('hidden');
      var span = warn.querySelector('[data-age-band-text]');
      if (span) {
        span.textContent = band === 'abandoned'
          ? 'These results are over a year old and may no longer reflect the library.'
          : 'These results are more than six months old.';
      }
    }
  });
})();
