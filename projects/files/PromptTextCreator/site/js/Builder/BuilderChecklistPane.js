// js/Builder/BuilderChecklistPane.js
//
// Builder checklist groups editor (scoped).
// - Edits checklist groups for the builder/profile state
// - Stores data in Panes scoped state (no window globals)
// - Re-renders on state:changed:<stateKey>
//
// Expected state shape:
//   state.options = [
//     { title: "Group", items: [ { label: "Thing", selected?: false }, ... ] },
//   ]

(function () {
  'use strict';

  function ensureState(api, stateKey) {
    var s = api.state.get(stateKey);
    if (!s) {
      s = {
        form: {},
        styles: [],
        options: [],
        mode: 'template',
        template: '',
        prompt: '',
        ollama: null
      };
      api.state.set(stateKey, s);
    }
    if (!Array.isArray(s.options)) s.options = [];
    return s;
  }

  function syncFromDOM(groupsWrap, State, api, stateKey) {
    var result = [];
    var groups = groupsWrap.querySelectorAll('.builder-group');

    Array.prototype.forEach.call(groups, function (g) {
      var inputs = g.querySelectorAll('input');
      if (!inputs.length) return;

      var title = (inputs[0].value || '').trim();

      var items = Array.prototype.slice.call(inputs, 1)
        .map(function (inp) { return { label: (inp.value || '').trim() }; })
        .filter(function (it) { return it.label; });

      if (title) result.push({ title: title, items: items });
    });

    State.options = result;
    api.state.set(stateKey, State);
  }

  function itemRow(groupsWrap, State, api, stateKey, value, markLocalWrite) {
    var row = document.createElement('div');
    row.className = 'checklist-item-row';

    var input = document.createElement('input');
    input.placeholder = 'Item label';
    input.value = value || '';

    input.addEventListener('input', function () {
      markLocalWrite();
      syncFromDOM(groupsWrap, State, api, stateKey);
    });

    var btnRemove = document.createElement('button');
    btnRemove.type = 'button';
    btnRemove.className = 'mini danger';
    btnRemove.textContent = '×';
    btnRemove.addEventListener('click', function () {
      row.remove();
      markLocalWrite();
      syncFromDOM(groupsWrap, State, api, stateKey);
    });

    row.appendChild(input);
    row.appendChild(btnRemove);

    return row;
  }

  function addGroup(groupsWrap, State, api, stateKey, title, items, markLocalWrite) {
    title = title || '';
    items = items || [];

    var group = document.createElement('div');
    group.className = 'group builder-group';

    var lab = document.createElement('label');
    lab.textContent = 'Group';

    var titleInput = document.createElement('input');
    titleInput.placeholder = 'Group Title (e.g., Core Capabilities)';
    titleInput.value = title;

    titleInput.addEventListener('input', function () {
      markLocalWrite();
      syncFromDOM(groupsWrap, State, api, stateKey);
    });

    var titleWrap = document.createElement('div');
    titleWrap.className = 'checklist-title-wrap';
    titleWrap.appendChild(lab);
    titleWrap.appendChild(titleInput);

    var itemsWrap = document.createElement('div');
    itemsWrap.className = 'checklist-items-wrap';

    var inner = document.createElement('div');

    items.forEach(function (it) {
      inner.appendChild(
        itemRow(groupsWrap, State, api, stateKey, (it && it.label) || '', markLocalWrite)
      );
    });

    var btnAdd = document.createElement('button');
    btnAdd.type = 'button';
    btnAdd.className = 'mini';
    btnAdd.textContent = '+ Item';
    btnAdd.addEventListener('click', function () {
      inner.appendChild(itemRow(groupsWrap, State, api, stateKey, '', markLocalWrite));
      markLocalWrite();
      syncFromDOM(groupsWrap, State, api, stateKey);
    });

    itemsWrap.appendChild(inner);
    itemsWrap.appendChild(btnAdd);

    group.appendChild(titleWrap);
    group.appendChild(itemsWrap);
    groupsWrap.appendChild(group);

    markLocalWrite();
    syncFromDOM(groupsWrap, State, api, stateKey);
  }

  function render(container, api, stateKey, opts, markLocalWrite) {
    opts = opts || {};

    var titleText = opts.title || 'Checklist Groups';
    var defaultGroupTitle = opts.defaultGroup || 'Core Skills';

    var State = ensureState(api, stateKey);

    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--builder-checklists';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = titleText;

    var groupsWrap = document.createElement('div');
    groupsWrap.className = 'builder-checklist-groups';

    var btnAddGroup = document.createElement('button');
    btnAddGroup.type = 'button';
    btnAddGroup.className = 'mini';
    btnAddGroup.textContent = '+ Add Group';

    var actions = document.createElement('div');
    actions.className = 'actions';
    actions.appendChild(btnAddGroup);

    section.appendChild(h2);
    section.appendChild(groupsWrap);
    section.appendChild(actions);
    container.appendChild(section);

    btnAddGroup.addEventListener('click', function () {
      addGroup(groupsWrap, State, api, stateKey, '', [], markLocalWrite);
    });

    var existing = Array.isArray(State.options) ? State.options : [];

    if (existing.length) {
      existing.forEach(function (g) {
        addGroup(groupsWrap, State, api, stateKey, g.title, g.items || [], markLocalWrite);
      });
    } else {
      addGroup(groupsWrap, State, api, stateKey, defaultGroupTitle, [], markLocalWrite);
    }
  }

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('BuilderChecklistPane: missing Panes api');
    }

    var ds = container.dataset || {};
    var stateKey = ds.stateKey || 'TEXT_PROFILE';

    var opts = {
      title: ds.title || 'Checklist Groups',
      defaultGroup: ds.defaultGroup || 'Core Skills'
    };

    // Prevent re-render loops when *this pane* writes state on input.
    var ignoreNext = false;
    function markLocalWrite() {
      ignoreNext = true;
      setTimeout(function () { ignoreNext = false; }, 0);
    }

    render(container, api, stateKey, opts, markLocalWrite);

    // Re-render when state changes externally (e.g., ProfileLoaderPane loads a file).
    var off = api.events.on('state:changed:' + stateKey, function () {
      if (ignoreNext) return;
      render(container, api, stateKey, opts, markLocalWrite);
    });

    return {
      destroy: function () {
        if (off) off();
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('BuilderChecklistPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('builder-checklists', function (container, api) {
    container.classList.add('pane-builder-checklists');
    return initOne(container, api);
  });
})();