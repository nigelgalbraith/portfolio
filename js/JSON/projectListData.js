const PROJECT_LIST_DATA = [
  {
    "href": "projects/arcade-cabinet.html",
    "img": "images/thumbs/optimized/arcade.png",
    "alt": "DIY Projects thumbnail",
    "title": "Custom Arcade Cabinet",
    "description": `
      <ul>
        <li>Reused salvaged materials to build a full-sized MAME arcade cabinet.</li>
        <li>Added custom wiring and arcade style controls.</li>
        <li>Powered by an old Dell PC running HyperSpin.</li>
        <li>Emulates multiple retro consoles for an all in one nostalgic gaming setup.</li>
      </ul>
    `
  },
  {
    "href": "projects/GreenhousePlanterBox.html",
    "img": "images/thumbs/optimized/GreenhousePlanterBox.png",
    "alt": "GreenhousePlanterBox Thumbnail",
    "title": "Greenhouse Planter Boxes",
    "description": `
      <ul>
        <li>Designed and built modular planter boxes for a greenhouse.</li>
        <li>Used SketchUp to test layout and fit before construction.</li>
        <li>Considered access, durability, and future replacement.</li>
      </ul>
    `
  },
  {
    "href": "projects/kvm-lab.html",
    "img": "images/thumbs/optimized/kvm-lab-thumb.png",
    "alt": "KVM Virtual Lab thumbnail",
    "title": "Open-Source Ubuntu KVM Solution",
    "description": `
      <ul>
        <li>Explored replacing VMware with an open source stack using Ubuntu, QEMU, and Libvirt.</li>
        <li>Evaluated integration with Active Directory and domain authentication.</li>
        <li>Tested feasibility within real hardware and environment constraints.</li>
        <li>Identified architectural and deployment challenges in virtual lab design.</li>
      </ul>
    `
  },
  {
    "href": "projects/PortfolioWebsite.html",
    "img": "images/thumbs/optimized/PortfolioWebsite.png",
    "alt": "Portfolio Website Thumbnail",
    "title": "Portfolio Website",
    "description": `
      <ul>
        <li>Designed and built the site structure using modular HTML and CSS.</li>
        <li>Implemented JavaScript loaders to inject content dynamically.</li>
        <li>Created reusable page templates to keep the system maintainable.</li>
      </ul>
    `
  },
  {
    "href": "projects/QuizCreator.html",
    "img": "images/thumbs/optimized/Quiz.png",
    "alt": "Quiz Thumbnail",
    "title": "Quiz Creator",
    "description": `
      <ul>
        <li>Reads quiz questions and answers directly from Excel files.</li>
        <li>Converts them into an interactive, browser based quiz.</li>
        <li>Runs locally with no external dependencies.</li>
        <li>Includes answer explanations for self study and offline use.</li>
      </ul>
    `
  },
  {
    "href": "projects/sharepoint-gps.html",
    "img": "images/thumbs/optimized/sharepoint-gps-thumb.png",
    "alt": "SharePoint and GPS App thumbnail",
    "title": "SharePoint Database and GPS Based Tracking System",
    "description": `
      <ul>
        <li>Developed a SharePoint platform with mobile friendly workflows.</li>
        <li>Enabled field staff to access and update job data remotely.</li>
        <li>Integrated GPS logging to track signage and site checks automatically.</li>
        <li>Improved coordination and planning for traffic management teams.</li>
      </ul>
    `
  },
  {
    "href": "projects/TerraceGardens.html",
    "img": "images/thumbs/optimized/TerraceGardens.png",
    "alt": "TerraceGardens Thumbnail",
    "title": "Terrace Gardens",
    "description": `
      <ul>
        <li>Designed tiered planter layouts in SketchUp before building.</li>
        <li>Worked around tight and uneven spaces.</li>
        <li>Built with durability and straightforward maintenance in mind.</li>
        <li>Adapted the layout to suit the available space.</li>
      </ul>
    `
  },
  {
    "href": "projects/ThermaticAnalysis.html",
    "img": "images/thumbs/optimized/ThermaticAnalysis.png",
    "alt": "ThermaticAnalysis Thumbnail",
    "title": "Thermatic Analysis Web Tool",
    "description": `
      <ul>
        <li>Transforms Excel based thematic coding data into a web tool.</li>
        <li>Provides an interactive interface to explore and review themes.</li>
        <li>Built with Python for data processing and export.</li>
        <li>Helps structure findings more easily.</li>
      </ul>
    `
  },
  {
    "href": "projects/PowerShell-CloudBackup.html",
    "img": "images/thumbs/optimized/PowerShellBackup.png",
    "alt": "PowerShell Backup Tool Thumbnail",
    "title": "PowerShell Cloud Backup Tool",
    "description": `
      <ul>
        <li>Automates backups to Google Drive, Dropbox, or Mega.</li>
        <li>Offers zipped or file based modes for flexibility.</li>
        <li>Includes a GUI with shutdown integration.</li>
        <li>Uses customizable JSON configs for source, destination, and schedule.</li>
      </ul>
    `
  },
  {
    "href": "projects/Debian-SetupSuite.html",
    "img": "images/thumbs/optimized/DebianSetup.png",
    "alt": "Debian Setup Suite Thumbnail",
    "title": "Debian Setup Suite",
    "description": `
      <ul>
        <li>Unified Debian setup suite powered by a main loader and constants modules.</li>
        <li>Supports model aware installs and configuration (APT, DEB, etc.).</li>
        <li>Loader selects the correct constants, validates configs, and builds a plan.</li>
        <li>Executes pipelines with full logging and rotation policy.</li>
      </ul>
    `
  },
  {
    "href": "projects/TextCreator.html",
    "img": "images/thumbs/optimized/TextCreatorOllama.png",
    "alt": "Text Creator Thumbnail",
    "title": "Text Creator",
    "description": `
      <ul>
        <li>Local text generator powered by Ollama and Piper.</li>
        <li>Modular pane based UI with profile loading, custom fields, and checklists.</li>
        <li>Generates structured prompts and renders text with on page preview.</li>
        <li>Includes optional text to speech and a full profile builder interface.</li>
      </ul>
  `
  },
  {
    "href": "projects/LanguageTranslator.html",
    "img": "images/thumbs/optimized/LanguageTranslator.png",
    "alt": "Language Translator Thumbnail",
    "title": "Language Translator",
    "description": `
      <ul>
        <li>Self-hosted translation UI using LibreTranslate and Piper TTS.</li>
        <li>Supports English ↔ Spanish and English ↔ Chinese with natural sounding voices.</li>
        <li>Nginx reverse proxy provides API routes, additional Languages can be added easily</li>
        <li>Modular UI built with reusable panes for text input, previews, toggles, and TTS.</li>
      </ul>
  `
  }
];
