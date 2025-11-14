// js/TextEntryPane.js
//
// Simple pane that renders a titled textarea for text input.
// Used here for entering English text to be translated / spoken.
//
// HOW TO USE:
//
//   <div
//     data-pane="text-entry"
//     data-title="English"
//     data-textarea-id="english-text"
//     data-placeholder="Type English text here...">
//   </div>

(function () {

  function initOne(container) {
    var ds = container.dataset || {};

    var title       = ds.title || 'Text';
    var textareaId  = ds.textareaId || 'text-entry';
    var placeholder = ds.placeholder || 'Type here...';

    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = title;

    var wrapper = document.createElement('div');
    wrapper.className = 'field';

    var div = document.createElement('div');
    div.id = textareaId;
    div.className = 'letter';
    div.contentEditable = 'true';
    div.setAttribute('data-placeholder', placeholder);

    wrapper.appendChild(div);

    section.appendChild(h2);
    section.appendChild(wrapper);
    container.appendChild(section);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var panes = document.querySelectorAll('[data-pane="text-entry"]');
    Array.prototype.forEach.call(panes, initOne);
  });

})();