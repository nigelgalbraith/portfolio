// =========================================================
// Modal helper: renders a simple overlay modal with a title,
// body content, and standard close behaviors
// =========================================================

// site/src/ui/common/modal.js

// =========================================================
// Imports
// =========================================================

import { el } from './dom.js';

// =========================================================
// Modal entry point
// =========================================================

// ---------- Open a modal overlay with a title and content element ----------
export function openModal({ title, contentEl }) {
  // ---------- Create overlay and modal container ----------
  const overlay = el('div', 'modal-overlay');
  const modal = el('div', 'modal');

  // =========================================================
  // Modal header
  // =========================================================

  const header = el('div', 'modal__header');
  header.appendChild(el('div', 'modal__title', title || 'Details'));

  // ---------- Close button ----------
  const closeBtn = el('button', 'btn btn-secondary', 'Close');
  closeBtn.type = 'button';

  // =========================================================
  // Modal body
  // =========================================================

  const body = el('div', 'modal__body');
  body.appendChild(contentEl);

  // ---------- Assemble modal structure ----------
  header.appendChild(closeBtn);
  modal.appendChild(header);
  modal.appendChild(body);
  overlay.appendChild(modal);

  // =========================================================
  // Close behavior
  // =========================================================

  // ---------- Remove modal overlay from DOM ----------
  const close = () => overlay.remove();

  // ---------- Close on button click ----------
  closeBtn.addEventListener('click', close);

  // ---------- Close when clicking outside the modal ----------
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });

  // ---------- Close on Escape key ----------
  window.addEventListener(
    'keydown',
    (e) => { if (e.key === 'Escape') close(); },
    { once: true }
  );

  // =========================================================
  // Attach modal to document
  // =========================================================

  document.body.appendChild(overlay);
}
