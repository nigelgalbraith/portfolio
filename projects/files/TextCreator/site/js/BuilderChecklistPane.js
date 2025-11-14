// js/BuilderChecklistPane.js
//
// ===============================================
//  CHECKLIST GROUPS EDITOR PANE — HOW TO USE
// ===============================================
//
// This pane allows a user to define one or more
// "checklist groups". Each group has:
//
//   - a *Group Title*
//   - a list of *Item labels* (strings)
//
// It writes all data into the shared builder
// global state:
//
//     window[builderGlobal].options = [
//       { title: "Group Name", items: [ {label: "Item1"}, ... ] }
//     ]
//
// To place this pane on a page:
//
//   <div
//      data-pane="builder-checklists"
//      data-builder-global="LETTER_BUILDER_STATE"
//      data-profile-event="profileLoaded"
//      data-title="Checklist Groups"
//      data-default-group="Core Skills">
//   </div>
//
// Attributes:
//
//   data-builder-global  (optional)
//       The global object name storing builder state.
//       Default: "LETTER_BUILDER_STATE"
//
//   data-profile-event   (optional)
//       Event name that triggers the pane to refresh
//       with data from an externally-loaded profile.
//       Default: "profileLoaded"
//
//   data-title           (optional)
//       The title shown at the top of the pane.
//
//   data-default-group   (optional)
//       Title used for the first auto-created group
//       if no state.options exist.
//
//
// API:
//
//   window.BuilderChecklists.setFromArray(arr, globalName)
//       - Replace the entire State.options array and
//         re-render all checklist panes.
//
// ===============================================
//  IMPLEMENTATION
// ===============================================

(function () {

  // -------------------------------------------------------------------
  // Ensure the global builder state object exists.
  // Creates it with safe defaults if missing.
  // -------------------------------------------------------------------
  function ensureState(globalName) {
    var key = globalName || 'LETTER_BUILDER_STATE';
    if (!window[key]) {
      window[key] = {
        form: {},
        styles: [],
        options: [],     // <-- Checklist data stored here
        mode: 'template',
        template: '',
        prompt: '',
        ollama: null
      };
    }
    return window[key];
  }

  // -------------------------------------------------------------------
  // Convert all DOM groups + items into the State.options array.
  // Called whenever inputs change.
  // -------------------------------------------------------------------
  function syncFromDOM(groupsWrap, State) {
    var result = [];
    var groups = groupsWrap.querySelectorAll('.builder-group');

    Array.prototype.forEach.call(groups, function (g) {
      var inputs = g.querySelectorAll('input');
      if (!inputs.length) return;

      // First input = group title
      var title = (inputs[0].value || '').trim();

      // Remaining inputs = item labels
      var items = Array.prototype.slice.call(inputs, 1)
        .map(function (inp) {
          return { label: inp.value.trim() };
        })
        .filter(function (it) {
          return it.label;
        });

      if (title) {
        result.push({ title: title, items: items });
      }
    });

    State.options = result;
  }

  // -------------------------------------------------------------------
  // Create one checklist item row with:
  //   [input]  [remove (×) button]
  // -------------------------------------------------------------------
  function itemRow(groupsWrap, State, value) {
    var row = document.createElement('div');
    row.className = 'checklist-item-row';

    var input = document.createElement('input');
    input.placeholder = 'Item label';
    input.value = value || '';

    input.addEventListener('input', function () {
      syncFromDOM(groupsWrap, State);
    });

    // Remove item button
    var btnRemove = document.createElement('button');
    btnRemove.type = 'button';
    btnRemove.className = 'mini danger';
    btnRemove.textContent = '×';
    btnRemove.addEventListener('click', function () {
      row.remove();
      syncFromDOM(groupsWrap, State);
    });

    row.appendChild(input);
    row.appendChild(btnRemove);

    return row;
  }

  // -------------------------------------------------------------------
  // Add a new checklist *group* consisting of:
  //   - Title input
  //   - List of item rows
  //   - "+ Item" button
  // -------------------------------------------------------------------
  function addGroup(groupsWrap, State, title, items) {
    title = title || '';
    items = items || [];

    var group = document.createElement('div');
    group.className = 'group builder-group';

    var lab = document.createElement('label');
    lab.textContent = 'Group';

    // Group title input
    var titleInput = document.createElement('input');
    titleInput.placeholder = 'Group Title (e.g., Core Capabilities)';
    titleInput.value = title;

    titleInput.addEventListener('input', function () {
      syncFromDOM(groupsWrap, State);
    });

    // Wrap for label + title input
    var titleWrap = document.createElement('div');
    titleWrap.className = 'checklist-title-wrap';
    titleWrap.appendChild(lab);
    titleWrap.appendChild(titleInput);

    // Wrap for all item rows + '+ Item' button
    var itemsWrap = document.createElement('div');
    itemsWrap.className = 'checklist-items-wrap';

    var inner = document.createElement('div');

    // Populate existing items
    items.forEach(function (it) {
      inner.appendChild(itemRow(groupsWrap, State, it.label || ''));
    });

    // Button to add new item
    var btnAdd = document.createElement('button');
    btnAdd.className = 'mini';
    btnAdd.textContent = '+ Item';
    btnAdd.addEventListener('click', function () {
      inner.appendChild(itemRow(groupsWrap, State, ''));
      syncFromDOM(groupsWrap, State);
    });

    itemsWrap.appendChild(inner);
    itemsWrap.appendChild(btnAdd);

    group.appendChild(titleWrap);
    group.appendChild(itemsWrap);
    groupsWrap.appendChild(group);

    syncFromDOM(groupsWrap, State);
  }

  // -------------------------------------------------------------------
  // Render the entire checklist pane into the container.
  // -------------------------------------------------------------------
  function render(container, opts) {
    opts = opts || {};

    var builderGlobal = opts.builderGlobal || 'LETTER_BUILDER_STATE';
    var titleText = opts.title || 'Checklist Groups';
    var defaultGroupTitle = opts.defaultGroup || 'Core Skills';

    var State = ensureState(builderGlobal);

    // Clear container first
    container.innerHTML = '';

    // Main section wrapper
    var section = document.createElement('section');
    section.className = 'pane';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = titleText;

    var groupsWrap = document.createElement('div');
    groupsWrap.id = 'builder-checklist-groups';

    // Add-group button
    var btnAddGroup = document.createElement('button');
    btnAddGroup.className = 'mini';
    btnAddGroup.textContent = '+ Add Group';

    var actions = document.createElement('div');
    actions.className = 'actions';
    actions.appendChild(btnAddGroup);

    section.appendChild(h2);
    section.appendChild(groupsWrap);
    section.appendChild(actions);
    container.appendChild(section);

    // Clicking "+ Add Group"
    btnAddGroup.addEventListener('click', function () {
      addGroup(groupsWrap, State, '', []);
    });

    // Load existing state.options OR seed a default group
    var existing = Array.isArray(State.options) ? State.options : [];

    if (existing.length) {
      existing.forEach(function (g) {
        addGroup(groupsWrap, State, g.title, g.items || []);
      });
    } else {
      addGroup(groupsWrap, State, defaultGroupTitle, []);
    }
  }

  // -------------------------------------------------------------------
  // Replace State.options entirely with new array data.
  // Does NOT re-render by itself.
  // -------------------------------------------------------------------
  function setFromArray(arr, builderGlobal) {
    var State = ensureState(builderGlobal);
    State.options = Array.isArray(arr) ? arr.slice() : [];
  }

  // -------------------------------------------------------------------
  // Initialize one pane instance.
  // Reads container's data-* attributes.
  // Binds profile load event if configured.
  // -------------------------------------------------------------------
  function initOne(container) {
    var ds = container.dataset || {};

    var builderGlobal = ds.builderGlobal || ds.builderState || 'LETTER_BUILDER_STATE';
    var profileEvent = ds.profileEvent || 'profileLoaded';
    var title = ds.title || 'Checklist Groups';
    var defaultGroupTitle = ds.defaultGroup || 'Core Skills';

    var opts = {
      builderGlobal: builderGlobal,
      title: title,
      defaultGroup: defaultGroupTitle
    };

    // Initial draw
    render(container, opts);

    // If profile loading is enabled:
    if (profileEvent) {
      window.addEventListener(profileEvent, function (ev) {
        var profile = ev.detail && ev.detail.profile;
        if (!profile) return;

        // Update state from loaded profile
        setFromArray(profile.options || [], builderGlobal);

        // Re-render all checklist panes
        var all = document.querySelectorAll('[data-pane="builder-checklists"]');
        Array.prototype.forEach.call(all, function (c) {
          var cfg = c.dataset || {};
          render(c, {
            builderGlobal: cfg.builderGlobal || cfg.builderState || 'LETTER_BUILDER_STATE',
            title: cfg.title || 'Checklist Groups',
            defaultGroup: cfg.defaultGroup || 'Core Skills'
          });
        });
      });
    }
  }

  // -------------------------------------------------------------------
  // Auto-init all matching panes on DOM ready.
  // Expose a small helper API as window.BuilderChecklists.
  // -------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {

    var containers = document.querySelectorAll('[data-pane="builder-checklists"]');
    Array.prototype.forEach.call(containers, initOne);

    // Public API for manual control
    window.BuilderChecklists = {
      setFromArray: function (arr, globalName) {
        var g = globalName || 'LETTER_BUILDER_STATE';
        setFromArray(arr, g);

        var containers = document.querySelectorAll('[data-pane="builder-checklists"]');
        Array.prototype.forEach.call(containers, initOne);
      }
    };
  });

})();
