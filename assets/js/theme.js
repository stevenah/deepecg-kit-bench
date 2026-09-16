/* Three-state theme toggle: auto -> light -> dark -> auto.
 *
 * Three states, not two, because a two-state toggle traps the reader out of "follow my
 * system" forever after a single click -- there is no way back to auto without clearing
 * site data. `data-theme-source` records which of the two we are in, so the matchMedia
 * listener only applies while the reader has actually chosen auto.
 *
 * The initial resolution happens in an inline blocking script in _includes/head.html,
 * BEFORE the stylesheet, so the first paint is already correct. This file only handles
 * clicks and system changes afterwards.
 */
(function () {
  var KEY = 'deepecg-theme';
  // Dark first, matching ECGBench. An unset preference resolves to dark; light (the paper
  // palette) and auto are one click away, and while auto is selected the matchMedia
  // listener below keeps following the system.
  var DEFAULT = 'dark';
  var order = ['dark', 'light', 'auto'];
  var labels = { auto: 'Auto', light: 'Light', dark: 'Dark' };
  var glyphs = { auto: '◐', light: '☀', dark: '☾' };
  var titles = { auto: 'Following your system', light: 'Light theme', dark: 'Dark theme' };

  function current() {
    try { return localStorage.getItem(KEY) || DEFAULT; } catch (e) { return DEFAULT; }
  }

  function apply(mode) {
    var root = document.documentElement;
    if (mode === 'auto') {
      root.removeAttribute('data-theme');
      root.setAttribute('data-theme-source', 'system');
    } else {
      root.setAttribute('data-theme', mode);
      root.setAttribute('data-theme-source', 'user');
    }
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-label', 'Colour theme: ' + labels[mode] + '. Click to change.');
      btn.setAttribute('title', titles[mode] + ' — click to change');
      var g = btn.querySelector('[data-theme-glyph]');
      var t = btn.querySelector('[data-theme-label]');
      if (g) g.textContent = glyphs[mode];
      if (t) t.textContent = labels[mode];
    });
  }

  function cycle() {
    var next = order[(order.indexOf(current()) + 1) % order.length];
    try { localStorage.setItem(KEY, next); } catch (e) { /* private mode: session only */ }
    apply(next);
  }

  document.addEventListener('DOMContentLoaded', function () {
    apply(current());
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.addEventListener('click', cycle);
    });
  });

  if (window.matchMedia) {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    var onChange = function () { if (current() === 'auto') apply('auto'); };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }
})();
