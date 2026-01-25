// js/IntroPane.js
//
// Intro pane (PanesCore-scoped).
// - Injects static HTML content from a global INTRO_TEXT map.
// - No DOMContentLoaded scanning.
// - Registered as: data-pane="intro-text"
//
// Usage:
//   <div data-pane="intro-text" data-intro-key="chinese"></div>
//
// Requires intro.js to run first (it can set window.INTRO_TEXT).

(function () {
  'use strict';

  function getIntroHTML(key) {
    var map = (window && window.INTRO_TEXT) ? window.INTRO_TEXT : null;
    if (!map) return '';
    if (!key) key = 'main';
    return map[key] || '';
  }

  function initOne(container, api) {
    // api is unused for now, but keeping signature consistent
    var ds = container.dataset || {};
    var key = ds.introKey || 'main';

    var html = getIntroHTML(key);
    container.innerHTML = html || '';

    return {
      destroy: function () {
        // no-op (we leave content in place)
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('IntroPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('intro-text', function (container, api) {
    container.classList.add('pane-intro-text');
    return initOne(container, api);
  });
})();