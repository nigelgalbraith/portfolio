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
      <li>Designed and built modular planter boxes for a greenhouse layout.</li>
      <li>Used SketchUp to test layout, fit, and spacing before construction.</li>
      <li>Planned for easy access, durability, and future replacement.</li>
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
      <li>Built raised vegetable beds to reduce bending while gardening.</li>
      <li>Used corrugated iron sides for durability and lower cost.</li>
      <li>Designed the layout in SketchUp before construction.</li>
      <li>Focused on practical access and long-term outdoor use.</li>
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
      <li>Designed a vertical greenhouse layout to maximise growing space.</li>
      <li>Used a stacked planter arrangement to improve access and watering.</li>
      <li>Built the frame to handle heat and humidity inside the greenhouse.</li>
      <li>Explores space-efficient small-scale food growing.</li>
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
      <li>Built a SharePoint platform with mobile-friendly workflows for field teams.</li>
      <li>Enabled staff to access and update job data directly from site.</li>
      <li>Integrated GPS logging to record signage locations and site inspections.</li>
      <li>Improved coordination and planning for traffic management operations.</li>
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
      <li>Tested replacing VMware with an open-source stack using Ubuntu, QEMU, and Libvirt.</li>
      <li>Evaluated integration with Active Directory and domain authentication.</li>
      <li>Built and configured a working KVM-based virtual lab environment.</li>
      <li>Documented architectural and deployment challenges in the setup.</li>
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
      <li>Designed and built a modular portfolio website using HTML, CSS, and JavaScript.</li>
      <li>Implemented JavaScript loaders to inject project data and page content dynamically.</li>
      <li>Used reusable page structures to keep layout, content, and logic separated.</li>
      <li>Built to remain maintainable as new projects are added.</li>
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
      <li>Reads quiz questions and answers directly from Excel spreadsheets.</li>
      <li>Converts the data into an interactive browser-based quiz.</li>
      <li>Runs locally in the browser with no external dependencies.</li>
      <li>Supports answer explanations for self-study and offline use.</li>
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
      <li>Converts Excel-based thematic coding data into an interactive web interface.</li>
      <li>Allows themes and coded responses to be explored and reviewed in the browser.</li>
      <li>Uses Python to process, organise, and export the dataset.</li>
      <li>Helps structure and navigate qualitative research findings.</li>
    </ul>
  `
},
{
  "href": "projects/DataAnalysisTool.html",
  "img": "images/thumbs/optimized/DataAnalysisTool.png",
  "alt": "Data Analysis Tool Thumbnail",
  "title": "Data Analysis Tool",
  "description": `
    <ul>
      <li>Containerised data analysis platform built with Python, Docker, and Nginx.</li>
      <li>Supports importing structured datasets and converting CSV data to SQL.</li>
      <li>Provides modular API routes for processing and exploring datasets.</li>
      <li>Designed as a flexible environment for building data analysis tools.</li>
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
      <li>Automates backups to Google Drive, Dropbox, and Mega.</li>
      <li>Supports both zipped and file-based backup modes.</li>
      <li>Includes a GUI with optional backup-before-shutdown integration.</li>
      <li>Uses JSON configuration files for source, destination, and backup settings.</li>
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
      <li>Built a unified Debian setup suite around a main loader and constants modules.</li>
      <li>Supports model-aware installs and configuration for APT, DEB, and related tasks.</li>
      <li>The loader selects constants, validates configuration, and builds an execution plan.</li>
      <li>Runs setup pipelines with structured logging and log rotation.</li>
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
      <li>Built reusable automation tools around a modular loader system.</li>
      <li>Tools are defined using constants modules and JSON configuration files.</li>
      <li>Supports validation, execution pipelines, and structured logging.</li>
      <li>Simplifies building reliable terminal-based automation tools.</li>
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
      <li>Built a network diagnostics toolkit on top of the automation loader framework.</li>
      <li>Includes Wi-Fi scanning, interface inspection, and TCP port scanning.</li>
      <li>Uses shared modules and configuration-driven tool definitions.</li>
      <li>Provides practical tools for diagnosing network connectivity issues.</li>
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
      <li>Local text generation tool powered by Ollama and Piper.</li>
      <li>Modular pane-based interface with profile loading, custom fields, and checklists.</li>
      <li>Builds structured prompts and renders generated text with on-page preview.</li>
      <li>Includes optional text-to-speech and a profile builder interface.</li>
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
      <li>Self-hosted translation interface using LibreTranslate and Piper TTS.</li>
      <li>Supports English ↔ Spanish and English ↔ Chinese translation with local voice output.</li>
      <li>Uses an Nginx reverse proxy to provide API routes for the interface.</li>
      <li>Designed to run fully locally using Docker.</li>
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
      <li>Web-based prompt builder designed for local AI models.</li>
      <li>Supports reusable prompt profiles and structured templates.</li>
      <li>Includes batch prompt generation and model selection.</li>
      <li>Built with a lightweight frontend and local API integration.</li>
    </ul>
  `
}

];