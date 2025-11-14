// js/GeneratorChecklistPane.js
//
// ===============================================
//  GENERATOR CHECKLIST PANE — HOW TO USE
// ===============================================
//
// This pane displays the grouped checklist options *on the generator page*.
// It reads the profile’s checklist groups (profile.options[]) and renders:
//
//   • A pane per group
//   • A list of checkboxes per group
//   • “Select All” / “Clear” buttons
//   • data-group + data-label attributes on checkboxes
//
// The GeneratorPreviewPane later reads these checkboxes to build its context.
//
// -----------------------------------------------
// 1) Add to HTML:
//
//   <div
//     data-pane="generator-checklists"
//     data-profile-event="profileLoaded"
//     data-profile-global="LETTER_PROFILE"
//     data-default-title="Options">
//   </div>
//
//
// -----------------------------------------------
// 2) Profile Requirements:
//
// The profile injected through event/global must include:
//   {
//     options: [
//       {
//         title: "Core Skills",
//         items: [ { label: "Leadership", selected: false }, ... ]
//       }
//     ]
//   }
//
// The BuilderChecklistPane already produces this format.
//
// -----------------------------------------------
// 3) data-* Attributes:
//
//   data-profile-event
//       Event name emitted when a profile loads.
//       Default: "profileLoaded"
//
//   data-profile-global
//       If set, pane renders immediately from window[profileGlobal].
//       Default: "LETTER_PROFILE"
//
//   data-default-title
//       Fallback group title if missing from profile.
//       Default: "Options"
//
// -----------------------------------------------
// 4) What this pane does:
//
//   • When profile loads → renders checklist groups
//   • Each checkbox gets:
//         cb.dataset.group = <slug>
//         cb.dataset.label = <item.label>
//     Used by GeneratorPreviewPane.buildCtx()
//
//   • Includes “Select All” and “Clear” buttons
//   • Maintains item.selected state in memory (not global)
//
// ===============================================
//  IMPLEMENTATION
// ===============================================

(function () {
  var FLASH_DURATION = 1200;

  // -------------------------------------------------------------------
  // Convert a group title to a slug identifier for checkbox dataset.
  // Example: "Core Capabilities" → "core_capabilities"
  // -------------------------------------------------------------------
  function toSlug(title) {
    return String(title || '')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
  }

  // -------------------------------------------------------------------
  // Display a temporary flash message under the group
  // -------------------------------------------------------------------
  function flash(flashDiv, msg, timeout) {
    if (!flashDiv) return;
    flashDiv.textContent = msg || '';
    flashDiv.classList.add('show');
    setTimeout(function () {
      flashDiv.classList.remove('show');
    }, timeout || FLASH_DURATION);
  }

  // -------------------------------------------------------------------
  // Render *one* checklist group:
  // <section class="pane checklist-group"> ... checkboxes ... </section>
  // -------------------------------------------------------------------
  function renderOneGroup(group, container, defaultTitle) {
    var section = document.createElement('section');
    section.className = 'pane checklist-group';

    // Group title
    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = group.title || defaultTitle || 'Options';

    // "Select All" + "Clear"
    var actions = document.createElement('div');
    actions.className = 'actions';

    var btnAll = document.createElement('button');
    btnAll.className = 'mini';
    btnAll.textContent = 'Select All';

    var btnNone = document.createElement('button');
    btnNone.className = 'mini';
    btnNone.textContent = 'Clear';

    actions.appendChild(btnAll);
    actions.appendChild(btnNone);

    // Container for checkbox rows
    var list = document.createElement('div');
    list.className = 'checklist';

    // Flash area
    var flashDiv = document.createElement('div');
    flashDiv.className = 'flash';

    // Unique group slug for dataset.group
    var slug = toSlug(group.title || defaultTitle || 'options');

    // -----------------------------------------------------
    // Render the individual checkboxes
    // -----------------------------------------------------
    function renderList() {
      list.innerHTML = '';

      (group.items || []).forEach(function (item) {
        var row = document.createElement('div');
        row.className = 'checkrow';

        var lab = document.createElement('label');
        lab.textContent = item.label || '';

        var cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = !!item.selected;

        // Used by GeneratorPreviewPane.buildCtx()
        cb.dataset.group = slug;
        cb.dataset.label = item.label || '';

        cb.addEventListener('change', function () {
          item.selected = cb.checked;
        });

        row.appendChild(lab);
        row.appendChild(cb);
        list.appendChild(row);
      });
    }

    // Select all items in this group
    btnAll.addEventListener('click', function () {
      (group.items || []).forEach(function (i) { i.selected = true; });
      renderList();
      flash(flashDiv, 'All selected');
    });

    // Clear all items in this group
    btnNone.addEventListener('click', function () {
      (group.items || []).forEach(function (i) { i.selected = false; });
      renderList();
      flash(flashDiv, 'Cleared');
    });

    // Initial render of checkboxes
    renderList();

    // Build group DOM
    section.appendChild(h2);
    section.appendChild(actions);
    section.appendChild(list);
    section.appendChild(flashDiv);

    container.appendChild(section);
  }

  // -------------------------------------------------------------------
  // Render all groups for a given profile
  // -------------------------------------------------------------------
  function renderAll(container, profile, defaultTitle) {
    container.innerHTML = '';

    var groups = Array.isArray(profile && profile.options)
      ? profile.options
      : [];

    groups.forEach(function (g) {
      renderOneGroup({
        title: g.title || defaultTitle || 'Options',
        items: (g.items || []).map(function (it) {
          return {
            label: it.label || '',
            selected: !!it.selected
          };
        })
      }, container, defaultTitle);
    });
  }

  // -------------------------------------------------------------------
  // Initialize one generator checklist pane
  // -------------------------------------------------------------------
  function initOne(container) {
    var ds = container.dataset || {};

    var eventName     = ds.profileEvent || ds.profileEventName || 'profileLoaded';
    var profileGlobal = ds.profileGlobal || 'LETTER_PROFILE';
    var defaultTitle  = ds.defaultTitle || 'Options';

    // 1) Render immediately if a profile is already present
    if (window[profileGlobal]) {
      renderAll(container, window[profileGlobal], defaultTitle);
    }

    // 2) Re-render when the profileLoaded event fires
    window.addEventListener(eventName, function (ev) {
      var profile = ev.detail && ev.detail.profile;
      if (!profile) return;
      renderAll(container, profile, defaultTitle);
    });
  }

  // -------------------------------------------------------------------
  // Auto-init all generator checklist panes
  // -------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    var containers = document.querySelectorAll('[data-pane="generator-checklists"]');
    if (!containers.length) return;
    Array.prototype.forEach.call(containers, initOne);
  });

})();
