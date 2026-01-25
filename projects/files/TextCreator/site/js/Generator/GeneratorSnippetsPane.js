// js/Generator/GeneratorSnippetsPane.js
//
// Generator snippets pane (scoped).
// - Renders reusable blocks from profile.snippets[]
// - Each item has a checkbox (selected) to include in prompt/template
// - Does NOT write to global state (only mutates the in-memory profile object)
//   which is used at generation time via DOM scraping (GeneratorPreviewPane)

(function () {
  'use strict';

  var FLASH_DURATION = 1200;

  function flash(flashDiv, msg, timeout) {
    if (!flashDiv) return;
    flashDiv.textContent = msg || '';
    flashDiv.classList.add('show');
    setTimeout(function () {
      flashDiv.classList.remove('show');
    }, timeout || FLASH_DURATION);
  }

  function renderOneItem(item, list) {
    var card = document.createElement('div');
    card.className = 'snippet-card';

    var head = document.createElement('div');
    head.className = 'snippet-head';

    var subject = document.createElement('div');
    subject.className = 'snippet-subject';
    subject.textContent = item.subject || '';

    var include = document.createElement('label');
    include.className = 'snippet-include';

    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = item.selected !== false;
    cb.dataset.role = 'snippet-selected';
    cb.dataset.subject = item.subject || '';

    cb.addEventListener('change', function () {
      item.selected = cb.checked;
    });

    var span = document.createElement('span');
    span.textContent = 'Use';

    include.appendChild(cb);
    include.appendChild(span);

    head.appendChild(subject);
    head.appendChild(include);

    var body = document.createElement('div');
    body.className = 'snippet-body';

    var ta = document.createElement('textarea');
    ta.readOnly = true;
    ta.rows = 4;
    ta.value = item.text || '';
    ta.dataset.role = 'snippet-text';
    ta.dataset.subject = item.subject || '';

    body.appendChild(ta);

    card.appendChild(head);
    card.appendChild(body);
    list.appendChild(card);
  }

  function render(container, profile, defaultTitle) {
    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--generator-snippets';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = defaultTitle || 'Snippets';

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
    list.className = 'snippet-list';

    var flashDiv = document.createElement('div');
    flashDiv.className = 'flash';

    var items = Array.isArray(profile && profile.snippets) ? profile.snippets : [];

    function rerenderList() {
      list.innerHTML = '';
      items.forEach(function (it) {
        // Skip empty rows quietly
        if (!it) return;
        if (!String(it.subject || '').trim() && !String(it.text || '').trim()) return;
        renderOneItem(it, list);
      });
    }

    btnAll.addEventListener('click', function () {
      items.forEach(function (i) { if (i) i.selected = true; });
      rerenderList();
      flash(flashDiv, 'All selected');
    });

    btnNone.addEventListener('click', function () {
      items.forEach(function (i) { if (i) i.selected = false; });
      rerenderList();
      flash(flashDiv, 'Cleared');
    });

    rerenderList();

    section.appendChild(h2);
    section.appendChild(actions);
    section.appendChild(list);
    section.appendChild(flashDiv);
    container.appendChild(section);
  }

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('GeneratorSnippetsPane: missing Panes api');
    }

    var ds = container.dataset || {};
    var stateKey = ds.stateKey || 'TEXT_PROFILE';
    var defaultTitle = ds.defaultTitle || 'Snippets';

    function rerenderFromState() {
      var profile = api.state.get(stateKey);
      if (!profile) {
        container.innerHTML = '';
        return;
      }
      render(container, profile, defaultTitle);
    }

    rerenderFromState();

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
    throw new Error('GeneratorSnippetsPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('generator-snippets', function (container, api) {
    container.classList.add('pane-generator-snippets');
    return initOne(container, api);
  });
})();
