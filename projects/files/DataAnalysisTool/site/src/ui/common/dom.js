// ==================================================
// DOM helpers
// ==================================================

export const el = (tag, className, text) => {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text !== undefined) n.textContent = text;
  return n;
};

// --------------------------------------------------
// Layout helpers
// --------------------------------------------------

export const createCenteredButtonRow = () => el('div', 'center-buttons');
