const PROJECT_LIST_DATA = [

/* -------------------------
   DIY / BUILD PROJECTS
------------------------- */

{
  "href": "projects/arcade-cabinet.html",
  "img": "images/thumbs/optimized/arcade.png",
  "alt": "DIY Projects thumbnail",
  "title": "Custom Arcade Cabinet",
  "description": `
    <ul>
      <li>Built a full-sized MAME arcade cabinet using salvaged materials.</li>
      <li>Installed custom wiring and arcade-style controls.</li>
      <li>Repurposed an old Dell PC running HyperSpin as the emulator system.</li>
      <li>Supports multiple retro console and arcade platforms.</li>
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
      <li>Designed tiered planter layouts in SketchUp before construction.</li>
      <li>Adapted the design to work around tight and uneven spaces.</li>
      <li>Built for durability and simple long-term maintenance.</li>
      <li>Optimised the layout to make better use of the available space.</li>
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
  "href": "projects/VegeGardenBoxes.html",
  "img": "images/thumbs/optimized/VegeGardenBoxes.png",
  "alt": "Vegetable Garden Boxes Thumbnail",
  "title": "Vegetable Garden Boxes",
  "description": `
    <ul>
      <li>Raised vegetable beds designed to reduce bending while gardening.</li>
      <li>Built using corrugated iron sides for durability and low cost.</li>
      <li>Designed in SketchUp before construction.</li>
      <li>Focused on practical access and long term outdoor use.</li>
    </ul>
  `
},
{
  "href": "projects/VerticalGreenhouse.html",
  "img": "images/thumbs/optimized/VerticalGreenhouse.png",
  "alt": "Vertical Greenhouse Thumbnail",
  "title": "Vertical Greenhouse",
  "description": `
    <ul>
      <li>Vertical greenhouse design to maximise growing space.</li>
      <li>Stacked planter layout improves access and watering.</li>
      <li>Frame designed for durability in greenhouse heat.</li>
      <li>Explores space efficient small scale food growing.</li>
    </ul>
  `
},

/* -------------------------
   INFRASTRUCTURE PROJECTS
------------------------- */

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

/* -------------------------
   SOFTWARE TOOLS
------------------------- */

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

/* -------------------------
   AUTOMATION SYSTEMS
------------------------- */

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
  "href": "projects/AutomationTools.html",
  "img": "images/thumbs/optimized/AutomationTools.png",
  "alt": "Automation Tools Thumbnail",
  "title": "Automation Tools",
  "description": `
    <ul>
      <li>Reusable automation tools built around a modular loader system.</li>
      <li>Tools are defined through constants modules and JSON configurations.</li>
      <li>Supports validation, execution pipelines, and structured logging.</li>
      <li>Designed to simplify building reliable terminal based automation tools.</li>
    </ul>
  `
},
{
  "href": "projects/TestingTools.html",
  "img": "images/thumbs/optimized/TestingTools.png",
  "alt": "Testing Tools Thumbnail",
  "title": "Network Testing Tools",
  "description": `
    <ul>
      <li>Network diagnostics toolkit built on the automation loader.</li>
      <li>Includes Wi-Fi scanning, interface inspection, and TCP port scanning.</li>
      <li>Uses shared modules and configuration driven tool definitions.</li>
      <li>Demonstrates how the loader framework can support real world diagnostics.</li>
    </ul>
  `
},

/* -------------------------
   AI / LLM TOOLS
------------------------- */

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
      <li>Nginx reverse proxy provides API routes and modular UI panes.</li>
      <li>Designed to run fully locally with Docker.</li>
    </ul>
  `
},
{
  "href": "projects/PromptForge.html",
  "img": "images/thumbs/optimized/PromptForge.png",
  "alt": "Prompt Forge Thumbnail",
  "title": "Prompt Forge",
  "description": `
    <ul>
      <li>Web based prompt building tool designed for local AI models.</li>
      <li>Supports reusable prompt profiles and structured prompt templates.</li>
      <li>Includes batch generation and model selection.</li>
      <li>Built with a lightweight frontend and local API integration.</li>
    </ul>
  `
}

];