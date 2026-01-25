// js/ButtonSwitch.js
//
// Lane switcher (PanesCore-scoped) — Option B controller.
//
// This version supports a SINGLE controller pane that switches visibility
// for a group of "lane" containers that are NOT panes themselves.
//
// HOW TO USE:
//
//   <!-- ONE controller -->
//   <div
//     data-pane="button-switch"
//     data-lane-selector='[data-lane="translate-lane"]'
//     data-ticker-id="profile-main"
//     data-label-prefix="Mode: "              // optional
//     data-button-prefix="Switch to: "        // optional
//   ></div>
//
//   <!-- MANY lanes (regular divs) -->
//   <div class="split" data-lane="translate-lane" data-title="English → Chinese"> ... </div>
//   <div class="split" data-lane="translate-lane" data-title="Chinese → English"> ... </div>
//
// NOTES:
// - Lanes can live anywhere in the DOM; they’re found via data-lane-selector.
// - Lane titles come from lane.dataset.title, else fallback to "Mode N".
// - Sends ticker messages via api.events.emit('ticker:temporary', ...)
// - Cleans up listeners on destroy().

(function () {
  'use strict';

  function notifyTicker(tickerId, text, ms, color, api) {
    if (!tickerId || !text) return;
    if (!api || !api.events || !api.events.emit) return;

    api.events.emit('ticker:temporary', {
      tickerId: tickerId,
      text: text,
      ms: ms,
      color: color
    });
  }

  function asArray(nodeList) {
    return Array.prototype.slice.call(nodeList || []);
  }

  function laneTitle(lane, idx) {
    if (!lane) return 'Mode ' + (idx + 1);
    return (lane.dataset && lane.dataset.title) || ('Mode ' + (idx + 1));
  }

  function setLaneVisible(lane, isVisible) {
    if (!lane) return;
    lane.style.display = isVisible ? '' : 'none';
    lane.dataset.active = isVisible ? 'true' : 'false';
  }

  function initOne(container, api) {
    if (!api || !api.events || !api.state) {
      throw new Error('ButtonSwitch: missing Panes api');
    }

    var ds = container.dataset || {};

    var laneSelector = ds.laneSelector || '[data-lane]';
    var tickerId = ds.tickerId || null;

    var labelPrefix = ds.labelPrefix || 'Mode: ';
    var buttonPrefix = ds.buttonPrefix || 'Switch to: ';

    var switchMsgPrefix = ds.switchMsgPrefix || 'Switched to ';

    // Find lanes
    var lanes = asArray(document.querySelectorAll(laneSelector));

    // Render nothing if no lanes found
    container.innerHTML = '';
    if (!lanes.length) {
      // Optional: you could render a tiny hint here, but silent is fine.
      return { destroy: function () {} };
    }

    // Hide all but first lane
    var activeIndex = 0;
    lanes.forEach(function (lane, idx) {
      setLaneVisible(lane, idx === 0);
    });

    // Build controls UI inside this pane host
    var controls = document.createElement('div');
    controls.className = 'actions button-switch-controls';

    var labelSpan = document.createElement('span');
    labelSpan.className = 'button-switch-label';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'secondary';

    function updateUI() {
      var currentTitle = laneTitle(lanes[activeIndex], activeIndex);
      var nextIndex = (activeIndex + 1) % lanes.length;
      var nextTitle = laneTitle(lanes[nextIndex], nextIndex);

      labelSpan.textContent = labelPrefix + currentTitle;
      btn.textContent = buttonPrefix + nextTitle;
    }

    function onClick() {
      // hide current
      setLaneVisible(lanes[activeIndex], false);

      // advance
      activeIndex = (activeIndex + 1) % lanes.length;

      // show next
      setLaneVisible(lanes[activeIndex], true);

      var title = laneTitle(lanes[activeIndex], activeIndex);
      notifyTicker(tickerId, switchMsgPrefix + title, 2500, 'var(--accent)', api);

      updateUI();
    }

    btn.addEventListener('click', onClick);
    updateUI();

    controls.appendChild(labelSpan);
    controls.appendChild(btn);
    container.appendChild(controls);

    return {
      destroy: function () {
        btn.removeEventListener('click', onClick);
        // (We don't auto-restore lanes on destroy; leaving DOM as-is is fine.)
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('ButtonSwitch requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('button-switch', function (container, api) {
    container.classList.add('pane-button-switch');
    return initOne(container, api);
  });
})();