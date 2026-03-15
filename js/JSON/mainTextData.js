// JSON/mainTextData.js
// Static JavaScript object used as embedded content data for main content rendering

const MAIN_TEXT_DATA = {
  /* -------------------------
     SITE CONTENT
  ------------------------- */

  "home": {
    "paragraphs": [
      "I’m an IT professional based in Christchurch, New Zealand, with experience in infrastructure, networking, virtualization, and automation. I enjoy building practical solutions, whether that’s for real systems, small tools, or hands-on projects.",
      "I started out in trades before moving into IT through study at Ara Institute of Canterbury. That mix of practical experience and technical learning still shapes how I approach systems and problem solving.",
      "For me the focus is always on making things work well in the real world. Good technology should simplify work, reduce friction, and make systems easier to manage.",
      "Feel free to explore the projects or get in touch if you'd like to talk about ideas, systems, or practical solutions."
    ]
  },

  "about": {
    "paragraphs": [
      "I'm Nigel Galbraith, an IT professional with a background in infrastructure, virtualization, and automation. I started out in trades before moving into technology, which gave me a practical way of thinking about systems and how they actually work in real environments.",
      "I enjoy solving complex problems and building solutions that are reliable, maintainable, and straightforward to use. For me, technology works best when it stays practical and focused on making things easier."
    ]
  },

  "contact": {
    "paragraphs": [
      "If you'd like to get in touch, here are a few ways to reach me.",
      "Feel free to send a message anytime."
    ],
    "lists": [
      {
        "items": [
          "Email: <a href=\"mailto:nigel.galbraith@proton.me\">nigelgalbraith@proton.me</a>",
          "GitHub: <a href=\"https://github.com/nigelgalbraith/\" rel=\"noopener\" target=\"_blank\">github.com/nigelgalbraith</a>",
          "LinkedIn: <a href=\"https://www.linkedin.com/in/nigel-galbraith\" rel=\"noopener\" target=\"_blank\">linkedin.com/in/nigel-galbraith</a>"
        ]
      }
    ]
  },

  /* -------------------------
     DIY / BUILD PROJECTS
  ------------------------- */

  "arcadeCabinet": {
    "paragraphs": [
      "I built a custom MAME arcade cabinet using waste MDF and salvaged timber from my joinery work, giving new life to materials that would otherwise have been discarded. The cabinet was designed from scratch and cut using basic woodworking tools, with a focus on keeping costs low while maintaining a classic arcade look.",
      "An i-PAC interface board handles keyboard inputs from the arcade buttons and joysticks, allowing standard arcade controls to work directly with the system.",
      "The cabinet runs Windows with HyperSpin as the frontend, supporting a library of over 4,000 classic games from various arcade systems and consoles. The project combines my interest in retro gaming with hands-on woodworking and hardware integration."
    ]
  },

  "terraceGardens": {
    "paragraphs": [
      "I designed the terrace garden layout in SketchUp, testing different planter box arrangements and levels to create a balanced and practical setup. The build was planned to stay straightforward and modular, using reclaimed wood and solid fixings to keep it durable while remaining easy to assemble.",
      "SketchUp allowed me to test layouts before building, which helped avoid mistakes and made the construction process smoother. Having a clear model also made it easier to explain the design and ensure everyone understood how the final structure would come together."
    ]
  },

  "greenhouseBoxes": {
    "paragraphs": [
      "I designed a series of modular planter box layouts in SketchUp to maximise growing space while keeping access simple. The design focused on modular construction so the boxes could be assembled easily inside the greenhouse.",
      "Using SketchUp allowed me to test layouts and dimensions before building, which helped avoid mistakes and made the final build more straightforward. It also made it easier to show the plan clearly and explain how the layout would fit together."
    ]
  },

  "vegeGardenBoxes": {
    "paragraphs": [
      "I built these raised vegetable garden boxes to make growing food easier without constant bending. The extra height makes planting, watering, and harvesting more comfortable.",
      "The design focused on durability and cost. Corrugated iron was used for the sides because it lasts longer than untreated timber and performs well outdoors.",
      "Before building, I modelled the layout in SketchUp to test dimensions and spacing. This helped plan the structure and made the final build easier to assemble."
    ]
  },

  "verticalGreenhouse": {
    "paragraphs": [
      "This project explores a vertical greenhouse layout designed to use space more efficiently. Instead of spreading planting trays across the ground, the trays are stacked vertically to increase growing area within the same footprint.",
      "The stacked drawer-style layout allows each level to be accessed from the front, making watering and maintenance easier while keeping the structure compact.",
      "After experimenting with materials, timber proved more reliable than plastic in the greenhouse environment. Plastic trays tended to become brittle from heat over time, while timber provided a more stable structure."
    ]
  },

  /* -------------------------
     INFRASTRUCTURE PROJECTS
  ------------------------- */

  "sharepointGps": {
    "paragraphs": [
      "While working at Downer, I developed a SharePoint-based system to improve communication and coordination within the traffic management team.",
      "The platform centralised Traffic Management Plans (TMPs), site checks, and planning tools into a single accessible system.",
      "It reduced paperwork and improved visibility between field crews and office staff, while also revealing the practical challenges of introducing digital workflows into established field operations."
    ],
    "lists": [
      {
        "title": "Key Features",
        "items": [
          "Access and manage Traffic Management Plans (TMPs) from tablets on site.",
          "Upload daily site checks using mobile devices.",
          "Scan traffic signs to log GPS coordinates."
        ]
      },
      {
        "title": "Operational Impact",
        "items": [
          "Forward works planning linking staff, plant, and resources.",
          "Shared weekly planner for improved visibility.",
          "Pre-planning support for crews based on job requirements."
        ]
      }
    ]
  },

  "kvmLab": {
    "paragraphs": [
      "The KVM Student Labs project explored replacing VMware Workstation Pro with an open-source stack built on Ubuntu, QEMU, and Libvirt. The goal was to reduce licensing costs while introducing domain-based authentication for managing student virtual machines.",
      "Integrating the Linux host with Active Directory and working through hardware compatibility proved more complex than expected. Limitations in the test environment required changes to the original plan and shifted the focus toward feasibility testing, reproducible setup steps, and clear documentation."
    ]
  },

  /* -------------------------
     SOFTWARE TOOLS
  ------------------------- */

  "portfolioWebsite": {
    "paragraphs": [
      "This project documents how I built my portfolio website, from the folder structure to the JavaScript that drives the site. The goal was to keep the system modular, maintainable, and framework-free.",
      "Pages are written as static HTML, with styling and behaviour handled through reusable JavaScript modules. Content is injected into templates, which keeps updates simple and avoids repeating code. Each project has its own page, while loaders handle shared elements such as images and footers.",
      "The structure keeps HTML, CSS, and JavaScript clearly separated. Building the site from scratch gave me full control over layout, accessibility, and performance while helping me deepen my understanding of front-end architecture."
    ]
  },

  "quizCreator": {
    "paragraphs": [
      "This project is a self-contained quiz generator that reads questions, answers, and explanations from a structured Excel spreadsheet and converts them into an interactive web quiz.",
      "The tool runs entirely offline with no sign-ups, external platforms, or internet connection required. Quizzes can be created and run locally, making it useful for personal study, classrooms, or environments with limited connectivity.",
      "I originally built it to support my own study process. Being able to generate quizzes from structured content made it easier to reinforce concepts and revisit topics as often as needed.",
      "The current version uses CyberOps material, but the system is flexible. By replacing the spreadsheet, the same tool can be used for subjects such as IT, science, languages, or general education.",
      "The project combines Python and pandas for spreadsheet processing with HTML, JavaScript, and JSON to generate the quiz interface. The focus was on keeping the system simple, practical, and easy to reuse."
    ]
  },

  "thematic": {
    "paragraphs": [
      "This project started as a way to manage thematic coding data in Excel without constantly jumping between sheets and manually tracking relationships between themes, factors, and notes.",
      "The workflow uses structured spreadsheets and macros to organise the data, while Python scripts handle processing and exporting the results.",
      "Working with qualitative datasets can get messy quickly, especially when themes, groupings, and notes start to grow. The goal of this setup was simply to keep everything organised and reduce the amount of repetitive spreadsheet work.",
      "The processed data can also be exported to a small web interface so the themes and relationships can be reviewed outside the spreadsheet."
    ]
  },

  "dataAnalysisTool": {
    "paragraphs": [
      "This project was built as a containerised environment for experimenting with different ways of processing and analysing structured datasets.",
      "The system combines a Python API, Docker containers, and an Nginx reverse proxy to create a modular platform where datasets can be imported, processed, and explored.",
      "Data can be imported from CSV files and converted into SQL-ready structures, allowing the analysis modules to work with consistent and structured datasets.",
      "The goal of the project was to build a flexible environment where new analysis tools could be added without rebuilding the entire system, keeping the data pipeline, processing logic, and interface separated."
    ]
  },

  "powerShellCloudBackup": {
    "paragraphs": [
      "This tool backs up selected files and folders to cloud storage such as Google Drive, Dropbox, or Mega before shutdown or logoff. It supports both zipped backups with retention and direct file copies using append or mirror mode. A simple GUI allows configuration of paths and settings, and the tool checks that cloud sync has completed before shutdown.",
      "Because mirror mode can remove files from the destination to match the source, it is recommended to run a manual backup first and confirm the paths are correct before enabling automatic backups on shutdown or logoff.",
      "Most cloud providers keep deleted files for a short period, which can help recover mistakes, but it is still important to verify the configuration before relying on automated backups.",
      "Backup settings are stored in JSON configuration files so they can be updated without modifying the script. Additional providers can be added by extending the `cloudProviders.json` configuration."
    ]
  },

  /* -------------------------
     AUTOMATION SYSTEMS
  ------------------------- */

  "debianInstallSuite": {
    "paragraphs": [
      "This project is a set of Python and Bash scripts that automate the setup of Debian-based systems using a modular, model-aware design. Each script handles a specific task such as installing packages, configuring firewall rules, setting up RDP, deploying services, or managing third-party repositories. Behaviour is controlled through JSON configuration files linked to system models.",
      "The workflow is straightforward: detect the system model, load the correct configuration, validate inputs, run the job, and log the results. Installers ask for confirmation before making changes, and logs are written to a versioned directory with automatic rotation.",
      "Instead of maintaining a single system image, the scripts allow different rules to be defined per device type and applied with a single command.",
      "Core logic is split into reusable utility modules for logging, service setup, permissions, and JSON handling. This keeps the scripts easier to extend and maintain as the project grows."
    ]
  },

  "automationTools": {
    "paragraphs": [
      "This project is a modular automation framework built around a single loader and a structured pipeline system. Instead of writing separate scripts for each task, tools are defined through constants modules, configuration files, validation rules, and reusable execution states.",
      "The loader handles shared tasks such as dependency checks, loading JSON configuration, validating inputs, building menus, and running the selected action through an ordered pipeline. This keeps tool-specific logic separate from the loader and makes the framework easier to extend.",
      "The project focuses on building predictable terminal-based automation tools using a consistent structure so new utilities can be added without rewriting the core workflow."
    ]
  },

  "testingTools": {
    "paragraphs": [
      "This project applies the same loader-based architecture to a set of terminal diagnostic tools. Instead of building separate scripts, the utilities share a common loader and pipeline structure for setup, validation, selection, and execution.",
      "Current tools include a Wi-Fi scanner and a network scanner. They can list interfaces, scan for nearby wireless networks, inspect selected network details, show ARP neighbours, and run TCP port scans against chosen hosts.",
      "Each tool has its own configuration and documentation, while shared modules handle the common execution flow so the utilities remain consistent and modular."
    ]
  },

  /* -------------------------
     AI / LLM TOOLS
  ------------------------- */

  "textCreator": {
    "paragraphs": [
      "This project is a standalone text generator designed to run entirely offline using Ollama and Piper. The goal was to create a simple, fast, and private tool that does not rely on external services or cloud APIs. Everything runs locally in Docker containers, with Nginx serving the interface.",
      "The system loads profile files that define prompt structure, form fields, and checklists. These inputs are assembled into a structured prompt and sent to the local language model to generate text. A profile builder interface allows templates and metadata to be created without editing JSON directly.",
      "Optional text-to-speech support is provided through Piper so generated text can be read aloud using local voice models. The application uses modular UI panes and avoids heavy frameworks, keeping the system lightweight and easy to deploy through Docker Compose."
    ]
  },

  "languageTranslator": {
    "paragraphs": [
      "This project is a self-hosted language translator built with LibreTranslate and Piper text-to-speech. The system runs entirely in Docker, with Nginx serving the frontend and proxying requests to the translation and voice services so everything stays local.",
      "The interface provides translation between English, Spanish, and Chinese. The UI is built from reusable panes for text input, translation output, controls, and audio playback. Each section is connected through data attributes so the same JavaScript modules can drive multiple translation directions.",
      "LibreTranslate performs the translation while Piper provides local voice output. Nginx exposes simple endpoints for translation and text-to-speech services, keeping the browser-side code straightforward."
    ]
  },

  "promptForge": {
    "paragraphs": [
      "Prompt Forge is a local prompt-building interface designed to run in Docker. It expands on the earlier Text Creator project by moving the workflow into a browser-based interface while keeping everything local and self-contained.",
      "The frontend is served through Nginx using vanilla JavaScript modules. A lightweight Node and Express API handles prompt generation and profile management. Profiles can be created, stored as JSON, and loaded back into the interface to reuse structured prompt setups.",
      "The system works with local model providers such as Ollama or LocalAI, with optional Piper text-to-speech support. The architecture keeps the browser UI, API layer, and local model services clearly separated."
    ]
  }
};
