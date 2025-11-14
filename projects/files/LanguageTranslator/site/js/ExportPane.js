// js/BuilderExportPane.js
//
// ===============================================
//  EXPORT PANE — HOW TO USE
// ===============================================
//
// This pane provides a single button that downloads
// the entire builder global state as a JSON file.
//
// Example output structure:
//   {
//     "form": { ... },
//     "styles": [ ... ],
//     "options": [ ... ],
//     "mode": "template" | "llm",
//     "template": "...",
//     "prompt": "...",
//     "ollama": { model, options }
//   }
//
// -----------------------------------------------
// 1) Add to your HTML:
//
//   <div
//     data-pane="builder-export"
//     data-builder-global="LETTER_BUILDER_STATE"
//     data-title="Export Profile"
//     data-filename="profile.json"
//     data-button-label="Save JSON"
//
//     data-ticker-id="profile-main"                 // optional
//     data-msg-export-empty="Nothing to export"     // optional
//     data-msg-export-saved="Saved {filename}"      // optional
//   ></div>
//
//
// -----------------------------------------------
// 2) data-* Attributes:
//
//   data-builder-global   (optional)
//       Name of the global builder state object to export.
//       Default: "LETTER_BUILDER_STATE"
//
//   data-title            (optional)
//       Title text shown above the button.
//       Default: "Export"
//
//   data-filename         (optional)
//       File name used for download.
//       Default: "profile.json"
//
//   data-button-label     (optional)
//       Text shown on the export button.
//       Default: "Download JSON"
//
//   data-ticker-id        (optional)
//       ID of StatusTickerPane to send temporary messages to.
//
//   data-msg-export-empty (optional)
//       Message when there is nothing to export.
//       Default: "Nothing to export"
//
//   data-msg-export-saved (optional)
//       Message when export succeeds.
//       "{filename}" will be replaced with the actual filename.
//       Default: "Saved {filename}"
//
//
// -----------------------------------------------
// 3) What this pane does:
//
//   - Creates a button
//   - When clicked:
//        → Reads window[builderGlobal]
//        → Converts it to JSON
//        → Starts a browser download
//        → Shows a temporary status message (5s then clears)
//        → Optionally notifies the ticker
//
//
// -----------------------------------------------
// 4) Requirements:
//
//   - Must be used alongside the other builder panes
//   - Assumes the builder global is in the expected shape
//
// ===============================================
//  IMPLEMENTATION
// ===============================================

(function () {

  var FLASH_DURATION_MS = 5000;

  // -------------------------------------------------------------------
  // Helper: ping the status ticker (StatusTickerPane.js)
  // -------------------------------------------------------------------
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

  // -------------------------------------------------------------------
  // Safely read a global variable by name.
  // Returns null if not present.
  // -------------------------------------------------------------------
  function readGlobal(name) {
    if (!name) return null;
    return window[name] || null;
  }

  // -------------------------------------------------------------------
  // Display a quick temporary message below the button.
  // Fades out after FLASH_DURATION_MS and clears text.
  // -------------------------------------------------------------------
  function flash(flashEl, msg) {
    flashEl.textContent = msg || '';
    flashEl.classList.add('show');
    setTimeout(function () {
      flashEl.classList.remove('show');
      flashEl.textContent = '';
    }, FLASH_DURATION_MS);
  }

  // -------------------------------------------------------------------
  // Initialize one export pane.
  // Reads data-* attributes and builds the export button UI.
  // -------------------------------------------------------------------
  function init(container) {
    var ds = container.dataset || {};

    var globalName   = ds.builderGlobal || 'LETTER_BUILDER_STATE';
    var title        = ds.title        || 'Export';
    var filename     = ds.filename     || 'profile.json';
    var buttonLabel  = ds.buttonLabel  || 'Download JSON';

    // Optional ticker
    var tickerId = ds.tickerId || null;

    // Messages (configurable via data-*)
    var msgExportEmpty = ds.msgExportEmpty || 'Nothing to export';
    var msgExportSaved = ds.msgExportSaved || 'Saved {filename}';

    // Clear container for render
    container.innerHTML = '';

    // Create pane structure
    var section = document.createElement('section');
    section.className = 'pane';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = title;

    var actions = document.createElement('div');
    actions.className = 'actions';

    var btn = document.createElement('button');
    btn.className = 'primary';
    btn.textContent = buttonLabel;

    var flashDiv = document.createElement('div');
    flashDiv.className = 'flash';

    actions.appendChild(btn);
    section.appendChild(h2);
    section.appendChild(actions);
    section.appendChild(flashDiv);
    container.appendChild(section);

    // ---------------------------------------------------------------
    // Button handler: export builder state to JSON and download file.
    // ---------------------------------------------------------------
    btn.addEventListener('click', function () {

      var obj = readGlobal(globalName);

      // No global state found?
      if (!obj) {
        flash(flashDiv, msgExportEmpty);
        notifyTicker(tickerId, msgExportEmpty, FLASH_DURATION_MS, '#f97316'); // orange-ish
        return;
      }

      // Create JSON blob
      var blob = new Blob([JSON.stringify(obj, null, 2)], {
        type: 'application/json'
      });

      // Create temporary <a> to trigger download
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = filename;

      document.body.appendChild(a);
      a.click();   // ← triggers download
      a.remove();

      URL.revokeObjectURL(url);

      var msg = msgExportSaved.replace('{filename}', filename);

      flash(flashDiv, msg);
      notifyTicker(tickerId, msg, FLASH_DURATION_MS, 'var(--accent)');
    });
  }

  // -------------------------------------------------------------------
  // Automatically initialize all [data-pane="builder-export"] panes.
  // -------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    var panes = document.querySelectorAll('[data-pane="builder-export"]');
    Array.prototype.forEach.call(panes, init);
  });

})();
