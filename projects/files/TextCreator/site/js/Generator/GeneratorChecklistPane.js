// js/Generator/GeneratorChecklistPane.js
//
// Generator checklist pane (scoped).
// - Renders grouped checklist options from profile.options[]
// - Reads profile from Panes scoped state
// - Re-renders on PanesCore state events: state:changed:<stateKey>

(function () {
  'use strict';

  var FLASH_DURATION = 1200;

  function toSlug(title) {
    return String(title || '')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
  }

  function flash(flashDiv, msg, timeout) {
    if (!flashDiv) return;
    flashDiv.textContent = msg || '';
    flashDiv.classList.add('show');
    setTimeout(function () {
      flashDiv.classList.remove('show');
    }, timeout || FLASH_DURATION);
  }

  function renderOneGroup(group, container, defaultTitle) {
    var section = document.createElement('section');
    section.className = 'pane checklist-group';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = group.title || defaultTitle || 'Options';

    var actions = document.createElement('div');
    actions.className = 'actions';

    var btnAll = document.createElement('button');
    btnAll.className = 'mini';
    btnAll.type = 'button';
    btnAll.textContent = 'Select All';

    var btnNone = document.createElement('button');
    btnNone.className = 'mini';
    btnNone.type = 'button';
    btnNone.textContent = 'Clear';

    actions.appendChild(btnAll);
    actions.appendChild(btnNone);

    var list = document.createElement('div');
    list.className = 'checklist';

    var flashDiv = document.createElement('div');
    flashDiv.className = 'flash';

    var slug = toSlug(group.title || defaultTitle || 'options');

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

    btnAll.addEventListener('click', function () {
      (group.items || []).forEach(function (i) { i.selected = true; });
      renderList();
      flash(flashDiv, 'All selected');
    });

    btnNone.addEventListener('click', function () {
      (group.items || []).forEach(function (i) { i.selected = false; });
      renderList();
      flash(flashDiv, 'Cleared');
    });

    renderList();

    section.appendChild(h2);
    section.appendChild(actions);
    section.appendChild(list);
    section.appendChild(flashDiv);

    container.appendChild(section);
  }

  function renderAll(container, profile, defaultTitle) {
    container.innerHTML = '';

    var groups = Array.isArray(profile && profile.options) ? profile.options : [];

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

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('GeneratorChecklistPane: missing Panes api');
    }

    var ds = container.dataset || {};

    var stateKey = ds.stateKey || 'TEXT_PROFILE';
    var defaultTitle = ds.defaultTitle || 'Options';

    function rerenderFromState() {
      var profile = api.state.get(stateKey);
      if (!profile) {
        container.innerHTML = '';
        return;
      }
      renderAll(container, profile, defaultTitle);
    }

    // Initial render if state already has a profile
    rerenderFromState();

    // Re-render whenever that state key changes
    var off = api.events.on('state:changed:' + stateKey, function () {
      rerenderFromState();
    });

    return {
      destroy: function () {
        if (off) off();
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('GeneratorChecklistPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('generator-checklists', function (container, api) {
    container.classList.add('pane-generator-checklists');
    return initOne(container, api);
  });
})();