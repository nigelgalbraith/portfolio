// js/ReflectionsLoader.js
// Controller class to handle injecting content from MAIN_TEXT_DATA into HTML elements

class ReflectionsLoader {
  static render(dataKey, dataSource, targetElement) {
    const content = dataSource[dataKey];
    if (!content || !targetElement) return;

    // Append heading (optional)
    if (content.heading) {
      const h2 = document.createElement('h2');
      h2.textContent = content.heading;
      targetElement.appendChild(h2);
    }

    // Append paragraphs
    content.paragraphs?.forEach(text => {
      const p = document.createElement('p');
      p.textContent = text;
      targetElement.appendChild(p);
    });

    // Append lists
    content.lists?.forEach(list => {
      if (list.title) {
        const heading = document.createElement('h3');
        heading.textContent = list.title;
        targetElement.appendChild(heading);
      }
      const ul = document.createElement('ul');
      list.items.forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = item;
        ul.appendChild(li);
      });
      targetElement.appendChild(ul);
    });
  }
}


// DOMContentLoaded: Look for elements with data-main-text and populate them
document.addEventListener("DOMContentLoaded", () => {
  const target = document.querySelector('[data-reflections-text]');
  if (!target) return;

  const key = target.dataset.reflectionsText;
  ReflectionsLoader.render(key, REFLECTIONS_DATA, target);
});
