// Apply theme to document and update toggle state
function applyTheme(theme) {
  const html = document.documentElement;
  html.dataset.theme = theme;
  localStorage.setItem("theme", theme);
  const btn = document.querySelector(".theme-toggle");
  if (btn) {
    const isLight = theme === "light";
    btn.setAttribute("aria-pressed", String(isLight));
    const icon = btn.querySelector(".theme-toggle-icon");
    if (icon) icon.textContent = isLight ? "☀" : "☾";
  }
}

// Initialize theme from saved/system preference and attach toggle listener
function initThemeToggle() {
  const saved = localStorage.getItem("theme");
  const systemPrefersLight = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
  const initial = saved || (systemPrefersLight ? "light" : "dark");
  applyTheme(initial);
  const btn = document.querySelector(".theme-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const current = document.documentElement.dataset.theme || "dark";
    applyTheme(current === "light" ? "dark" : "light");
  });
}

// Run on load (script is deferred)
initThemeToggle();