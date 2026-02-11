// Toggles the mobile navigation menu open/closed by adding or removing the 'active' class
function toggleMenu(button) {
  const navLinks = document.getElementById("navLinks");
  const isOpen = navLinks.classList.toggle("active");
  if (button) {
    button.setAttribute("aria-expanded", String(isOpen));
  }
}
