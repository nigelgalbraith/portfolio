// js/IntroPane.js
//
// ===============================================
//  INTRO PANE — HOW TO USE
// ===============================================
//
// This pane is responsible for injecting static HTML
// (intro text, help text, instructions, etc.) from a
// global object called INTRO_TEXT into any container.
//
// You typically define INTRO_TEXT in a separate file:
//    /text/intro.js
//
// Example of /text/intro.js:
//
//   window.INTRO_TEXT = {
//     main: `
//       <h1>Welcome to the Letter Generator</h1>
//       <p>This tool lets you build reusable profiles ...</p>
//     `,
//     about: `
//       <h2>About This Project</h2>
//       <p>All content is dynamically loaded via panes.</p>
//     `
//   };
//
// -----------------------------------------------
// 1) Add an intro pane to your HTML:
//
//   <div
//     data-pane="intro-text"
//     data-intro-key="main">
//   </div>
//
// The intro-key picks which entry from INTRO_TEXT to use.
// If omitted, it defaults to "main".
//
// -----------------------------------------------
// 2) Load /text/intro.js BEFORE this script:
//      <script src="/text/intro.js"></script>
//      <script src="/js/IntroPane.js"></script>
//
// -----------------------------------------------
// 3) Behavior:
//
//  • On DOMContentLoaded, all elements with
//    data-pane="intro-text" are scanned.
//
//  • The pane reads data-intro-key, e.g. "main", "about",
//    and replaces the element's content with the matching
//    HTML string from INTRO_TEXT.
//
//  • If no text exists for that key, the pane clears
//    the element (fails silently).
//
// ===============================================
//  IMPLEMENTATION
// ===============================================

(function () {

  /**
   * Initialize a single intro pane.
   * Reads the intro key and injects HTML from INTRO_TEXT.
   */
  function initOne(container) {
    var key = container.dataset.introKey || 'main';

    // If INTRO_TEXT or key missing, fallback to empty
    if (!window.INTRO_TEXT || !window.INTRO_TEXT[key]) {
      container.innerHTML = ''; // optional: fallback text
      return;
    }

    // Replace container HTML with the defined intro snippet
    container.innerHTML = window.INTRO_TEXT[key];
  }

  /**
   * Scan all <div data-pane="intro-text"> on DOM ready
   * and initialize each one independently.
   */
  document.addEventListener('DOMContentLoaded', function () {
    var panes = document.querySelectorAll('[data-pane="intro-text"]');
    for (var i = 0; i < panes.length; i++) {
      initOne(panes[i]);
    }
  });

})();
