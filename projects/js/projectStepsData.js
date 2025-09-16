// Function to generate and insert step content into the page
function loadProjectSteps(containerSelector, steps) {
  const container = document.querySelector(containerSelector);
  if (!container || !steps || steps.length === 0) return;

  // Loop through each step and build the corresponding HTML structure
  steps.forEach(({ title, img, alt, text }) => {
    // Create outer container for each step
    const box = document.createElement("div");
    box.className = "boxed-content";

    // Step title as a centered heading
    const h2 = document.createElement("h2");
    h2.className = "centered-title";
    h2.textContent = title;

    // Wrapper for zoomable image
    const wrapper = document.createElement("div");
    wrapper.className = "image-zoom-wrapper";

    // Placeholder div used by responsiveImageLoader to insert picture tags
    const imgDiv = document.createElement("div");
    imgDiv.className = "responsive-image";
    imgDiv.dataset.imgName = img;
    imgDiv.dataset.alt = alt;
    imgDiv.dataset.class = "centre-img"; // Styling class for centering

    wrapper.appendChild(imgDiv);

    // Text explanation for the step (supports string, HTML, or bullet arrays)
    let contentElement;

    if (Array.isArray(text)) {
      // If 'text' is an array, convert to bullet list
      contentElement = document.createElement("ul");
      text.forEach(point => {
        const li = document.createElement("li");
        li.textContent = point;
        contentElement.appendChild(li);
      });
    } else if (typeof text === "string" && text.includes("<li>")) {
      // If 'text' is an HTML list, insert using innerHTML
      contentElement = document.createElement("div");
      contentElement.innerHTML = text;
    } else {
      // Default case: plain paragraph text
      contentElement = document.createElement("p");
      contentElement.textContent = text;
    }

    // Wrap the text block inside a step-text container
    const textWrapper = document.createElement("div");
    textWrapper.className = "step-text";
    textWrapper.appendChild(contentElement);

    // Assemble all parts and append to the main container
    box.appendChild(h2);
    box.appendChild(wrapper);
    box.appendChild(textWrapper);
    container.appendChild(box);

    // Optional line break between steps for spacing
    container.appendChild(document.createElement("br"));
  });
}

// Automatically run once the page is fully loaded
document.addEventListener("DOMContentLoaded", () => {
  // Find the section in the page to inject content into
  const container = document.querySelector(".main-content-step-text section");

  // Identify the project type from the <body> data attribute
  const project = document.body.dataset.project;

  // Only proceed if matching project steps exist in ProjectSteps JSON
  if (container && ProjectSteps[project]) {
    loadProjectSteps(".main-content-step-text section", ProjectSteps[project]);
  }
});
