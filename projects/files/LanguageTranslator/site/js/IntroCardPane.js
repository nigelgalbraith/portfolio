// IntroCardPane.js
class IntroCardPane {
  constructor(element) {
    this.element = element;
    this.cardKey = element.dataset.cardKey;
    this.render();
  }

  render() {
    const card = introCards[this.cardKey];
    if (!card) {
      this.element.innerHTML = `<p>Card not found: ${this.cardKey}</p>`;
      return;
    }

    this.element.classList.add("translator-card");

    this.element.innerHTML = `
      <a href="${card.link}">
        <h2>${card.title}</h2>
        <p>${card.description}</p>
      </a>
    `;
  }
}

// Auto-init
document.querySelectorAll('[data-pane="intro-card"]').forEach(el => {
  new IntroCardPane(el);
});
