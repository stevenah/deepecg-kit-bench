/* Catalogue search, filters and column sorting, driven entirely by data-* attributes
 * emitted by Liquid. No data is duplicated into JavaScript: if a row is not in the DOM it
 * cannot be filtered or sorted, and there is no second copy of the catalogue to drift out
 * of sync.
 */
(function () {
  var search = document.getElementById('search');
  var rows = Array.prototype.slice.call(document.querySelectorAll('[data-row]'));
  var buttons = Array.prototype.slice.call(document.querySelectorAll('.filter-btn'));
  var selects = Array.prototype.slice.call(document.querySelectorAll('select[data-group]'));
  var sorters = Array.prototype.slice.call(document.querySelectorAll('th[data-sort]'));
  var counter = document.getElementById('filter-count');
  var empty = document.getElementById('filter-empty');
  if (!rows.length) return;

  // The order Liquid emitted, which is what an unsorted table returns to.
  rows.forEach(function (r, i) { r.dataset.index = i; });
  var bodies = [];
  rows.forEach(function (r) {
    if (bodies.indexOf(r.parentNode) === -1) bodies.push(r.parentNode);
  });

  var active = {};
  buttons.forEach(function (b) {
    if (b.classList.contains('active')) active[b.dataset.group] = b.dataset.filter;
  });
  selects.forEach(function (s) { active[s.dataset.group] = s.value; });

  var sort = { key: null, type: null, dir: 1 };

  function matches(row) {
    for (var group in active) {
      var want = active[group];
      if (want === 'all') continue;
      if (group === 'show') {
        var kit = row.dataset.implemented === 'yes';
        if (want === 'kit' && !kit) return false;
        if (want === 'field' && kit) return false;
        if (want === 'measured' && !(parseInt(row.dataset.measured, 10) > 0)) return false;
      } else if ((row.dataset[group] || '') !== want) {
        return false;
      }
    }
    var q = (search && search.value || '').trim().toLowerCase();
    if (!q) return true;
    return (row.dataset.text || '').toLowerCase().indexOf(q) !== -1;
  }

  function sortValue(row) {
    // A survey row has no measured tasks to count; it prints n/a, so it sorts as missing.
    if (sort.key === 'measured' && row.dataset.implemented !== 'yes') return null;
    var raw = row.dataset[sort.key];
    if (raw === undefined || raw === '') return null;
    return sort.type === 'num' ? parseFloat(raw) : raw;
  }

  function compare(a, b) {
    if (sort.key) {
      var x = sortValue(a), y = sortValue(b);
      // Missing values go last in both directions: an empty cell is not a small number.
      if (x === null || y === null) {
        if (x !== y) return x === null ? 1 : -1;
      } else if (x !== y) {
        return (x < y ? -1 : 1) * sort.dir;
      }
    }
    return a.dataset.index - b.dataset.index;
  }

  // Each family keeps its own table, so rows are sorted within their family.
  function order() {
    bodies.forEach(function (body) {
      rows.filter(function (r) { return r.parentNode === body; })
          .sort(compare)
          .forEach(function (r) { body.appendChild(r); });
    });
    sorters.forEach(function (th) {
      var on = th.dataset.sort === sort.key;
      th.setAttribute('aria-sort', on ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none');
    });
  }

  function run() {
    var shown = 0;
    rows.forEach(function (r) {
      var ok = matches(r);
      r.classList.toggle('hidden', !ok);
      if (ok) shown++;
    });
    // The # column counts the rows on screen, so it is rewritten whenever they change.
    bodies.forEach(function (body) {
      var n = 0;
      Array.prototype.forEach.call(body.querySelectorAll('[data-row]:not(.hidden)'), function (r) {
        var cell = r.querySelector('.num-cell');
        if (cell) cell.textContent = ++n;
      });
    });
    // Group headers whose rows are all hidden should go too, or the page reads as if a
    // family exists but is empty.
    document.querySelectorAll('[data-group-block]').forEach(function (block) {
      var any = block.querySelectorAll('[data-row]:not(.hidden)').length;
      block.classList.toggle('hidden', any === 0);
    });
    if (empty) empty.classList.toggle('hidden', shown !== 0);
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
      buttons.filter(function (o) { return o.dataset.group === g; }).forEach(function (o) {
        o.classList.toggle('active', o === b);
        o.setAttribute('aria-pressed', o === b ? 'true' : 'false');
      });
      run();
    });
  });
  selects.forEach(function (s) {
    s.addEventListener('change', function () {
      active[s.dataset.group] = s.value;
      run();
    });
  });
  // The first click gives the order a reader usually wants -- newest, largest, most measured,
  // or A to Z -- which is never the order the page loads in, so a click always shows. The
  // second reverses it and the third returns to the original order. The listener is on the
  // cell, not the button inside it, so the whole header is the target.
  sorters.forEach(function (th) {
    var first = th.dataset.sortType === 'num' ? -1 : 1;
    th.addEventListener('click', function () {
      if (sort.key !== th.dataset.sort) {
        sort = { key: th.dataset.sort, type: th.dataset.sortType, dir: first };
      } else if (sort.dir === first) {
        sort.dir = -first;
      } else {
        sort = { key: null, type: null, dir: 1 };
      }
      order();
      run();
    });
  });
  if (search) search.addEventListener('input', run);
  run();
})();
