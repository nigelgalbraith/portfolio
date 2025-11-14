// js/ButtonSwitch.js
//
// Simple lane switcher:
// - Finds all <div data-pane="button-switch"> blocks
// - Shows only one at a time
// - Renders a toggle button to switch between them
//
// Each block can set:
//   data-title      → label shown in the switcher (e.g. "English → Spanish")
//   data-ticker-id  → optional, ID for StatusTickerPane

(function () {

  function notifyTicker(tickerId, text, ms, color) {
    if (!tickerId || !text) return;
    var ev = new CustomEvent('ticker:temporary', {
      detail: {
        tickerId: tickerId,
        text: text,
        ms: ms,
        color: color
      }
    });
    window.dispatchEvent(ev);
  }

  function initSwitch() {
    var lanes = Array.prototype.slice.call(
      document.querySelectorAll('[data-pane="button-switch"]')
    );

    if (!lanes.length) return;

    // Use tickerId from the first lane (you can change this if needed)
    var tickerId = lanes[0].dataset.tickerId || null;

    // Hide all but first lane
    var activeIndex = 0;
    lanes.forEach(function (lane, idx) {
      lane.style.display = idx === 0 ? '' : 'none';
      lane.dataset.active = idx === 0 ? 'true' : 'false';
    });

    // Helper to get a nice label for each lane
    function getTitle(idx) {
      var lane = lanes[idx];
      return lane.dataset.title || ('Mode ' + (idx + 1));
    }

    // Create controls bar
    var controls = document.createElement('div');
    controls.className = 'actions button-switch-controls';

    var labelSpan = document.createElement('span');
    labelSpan.className = 'button-switch-label';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'secondary';
    
    function updateUI() {
      var currentTitle = getTitle(activeIndex);
      var nextIndex = (activeIndex + 1) % lanes.length;
      var nextTitle = getTitle(nextIndex);

      labelSpan.textContent = 'Mode: ' + currentTitle;
      btn.textContent = 'Switch to: ' + nextTitle;
    }

    btn.addEventListener('click', function () {
      // Hide current
      lanes[activeIndex].style.display = 'none';
      lanes[activeIndex].dataset.active = 'false';

      // Next
      activeIndex = (activeIndex + 1) % lanes.length;

      // Show new lane
      lanes[activeIndex].style.display = '';
      lanes[activeIndex].dataset.active = 'true';

      var title = getTitle(activeIndex);
      notifyTicker(tickerId, 'Switched to ' + title, 2500, 'var(--accent)');

      updateUI();
    });

    updateUI();

    controls.appendChild(labelSpan);
    controls.appendChild(btn);

    // Insert controls before the first lane
    var firstLane = lanes[0];
    firstLane.parentNode.insertBefore(controls, firstLane);
  }

  document.addEventListener('DOMContentLoaded', initSwitch);

})();
