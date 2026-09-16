/* Catalogue search and filter chips, driven entirely by data-* attributes emitted by
 * Liquid. No data is duplicated into JavaScript: if a row is not in the DOM it cannot be
 * filtered, and there is no second copy of the catalogue to drift out of sync.
 */
(function () {
  var search = document.getElementById('search');
  var rows = Array.prototype.slice.call(document.querySelectorAll('[data-row]'));
  var buttons = Array.prototype.slice.call(document.querySelectorAll('.filter-btn'));
  var counter = document.getElementById('filter-count');
  if (!rows.length) return;

  var active = {};
  buttons.forEach(function (b) {
    var g = b.dataset.group;
    if (b.classList.contains('active')) active[g] = b.dataset.filter;
  });

  function matches(row) {
    for (var group in active) {
      var want = active[group];
      if (want === 'all') continue;
      var have = row.dataset[group] || '';
      if (group === 'measured') {
        if (want === 'yes' && !(parseInt(have, 10) > 0)) return false;
        if (want === 'no' && parseInt(have, 10) > 0) return false;
      } else if (have !== want) {
        return false;
      }
    }
    var q = (search && search.value || '').trim().toLowerCase();
    if (!q) return true;
    return (row.dataset.text || '').toLowerCase().indexOf(q) !== -1;
  }

  function run() {
    var shown = 0;
    rows.forEach(function (r) {
      var ok = matches(r);
      r.classList.toggle('hidden', !ok);
      if (ok) shown++;
    });
    // Group headers whose rows are all hidden should go too, or the page reads as if a
    // family exists but is empty.
    document.querySelectorAll('[data-group-block]').forEach(function (block) {
      var any = block.querySelectorAll('[data-row]:not(.hidden)').length;
      block.classList.toggle('hidden', any === 0);
    });
    if (counter) {
      counter.textContent = shown === rows.length
        ? rows.length + ' architectures'
        : shown + ' of ' + rows.length + ' architectures';
    }
  }

  buttons.forEach(function (b) {
    b.addEventListener('click', function () {
      var g = b.dataset.group;
      active[g] = b.dataset.filter;
      buttons.filter(function (o) { return o.dataset.group === g; })
             .forEach(function (o) { o.classList.toggle('active', o === b); });
      run();
    });
  });
  if (search) search.addEventListener('input', run);
  run();
})();
