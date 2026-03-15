// JSON/ReflectionsTextData.js
// Static JavaScript object used as embedded content data for reflection content rendering

const REFLECTIONS_DATA = {
  arcadeCabinet: {
    heading: "Reflection",
      paragraphs: [
        "I originally built the cabinet around an older PC because it was available and powerful enough to run everything I needed. It worked, but it drew more power than necessary, produced more heat, and added weight and bulk inside the cabinet. If I built it again, I would design it around a Raspberry Pi from the start. Lower power consumption, less heat, smaller footprint, and the ability to run Linux cleanly would simplify the system and remove the need for Windows entirely.",
        "The current cabinet is built in three large sections and is quite heavy. It functions well, but it is not modular. If I were redesigning it, I would treat the cabinet as a shell and separate the computing unit and controls into removable modules. A Raspberry Pi could sit in a drawer style compartment for easy access, and control panels could be interchangeable inserts joystick, trackball, or racing controls depending on the game. The biggest lesson was to spend more time designing the system structure before building it, so each part can be upgraded or replaced independently."
      ]
  },
  debianInstallSuite: {
    heading: "Reflection",
      paragraphs: [
        "One of the early design decisions in this project was using the system model number to determine which configuration file to apply. That worked initially, but I realised two machines could share the same model while serving different roles. I changed the flow to prioritise computer name first, then model number, and finally fall back to a default. That small architectural adjustment made the system more predictable and flexible.",
        "As the project grew, the bigger challenge became code structure. With multiple modules and many small functions, it became harder to track what was actually in use and what wasn’t. Some functions began doing more than they should have, and early design shortcuts carried forward into later stages, which made retroactive fixes frustrating. To improve visibility, I built a constants and function scanning tool to detect unused functions and review docstrings. The main lesson was to slow down the initial framework design and resolve structural issues early, rather than pushing forward and repairing them later."
      ]
  },
  greenhouseBoxes: {
    heading: "Reflection",
      paragraphs: [
        "One of the main lessons from this build was something I already knew from joinery: a design can look great on paper but rarely fits perfectly in the real world. In this case, getting the planter boxes inside the greenhouse was more of a mission than expected. You have to think about access, doorways, space to manoeuvre, not just how it looks once it’s sitting in place.",
        "If I were doing it again, I would spend more time designing for future replacement. Timber in a greenhouse environment will eventually rot or deteriorate. A better system might use fixed metal posts with removable timber planks that slot in, similar to how the glass panels are installed in the greenhouse itself. That way, if a board fails, you just replace that section instead of rebuilding the whole structure. It’s doable, it just means thinking it through properly at the start and making sure it still makes sense cost wise."
      ]
  },
  kvmLab: {
    heading: "Reflection",
      paragraphs: [
        "One of the biggest realities in this project was that the original plan did not survive contact with the environment. Building inside a virtual test setup turned out to be unrealistic, so the solution had to be developed on a standalone machine instead. When something broke in that environment, it sometimes meant rebuilding parts of the system from scratch. That was frustrating, but it made one thing clear: reproducibility, scripting, and backups are not optional. If a system cannot be rebuilt cleanly, it is fragile.",
        "The project phases also looked much cleaner on paper than they did in practice. Deliverables overlapped, earlier decisions had to be revisited, and configuration changes often had ripple effects. It reinforced the need to slow down early architectural decisions, document as you go, and design with future changes in mind. The project proved KVM was viable, but more importantly, it exposed where planning assumptions break down and where stronger structure and documentation are needed from the start."
      ]
  },
  sharepointGps: {
    heading: "Reflection",
      paragraphs: [
        "On paper, the SharePoint system made sense. In practice, field conditions quickly exposed the gaps. Tablets ran flat, chargers were needed in vehicles, and touch screens were not always ideal in rain or on busy roadside sites. Coverage issues meant TMPs had to be saved locally, and paper copies were still required as a backup. It reinforced that digital solutions have to survive real-world environments, not just work in an office.",
        "The QR scanning system also showed practical limitations. Damaged codes required manual entry, and scanning signage after installation sometimes meant an extra run on site. Integrating tablets directly with company web servers also raised security concerns, so TMP distribution often relied on automated email instead. The biggest lesson was that efficiency gains on paper do not always translate cleanly into field operations. Systems need to be designed around human behaviour, environment constraints, and failure scenarios from the start."
      ]
  },
  "terraceGardens": {
    heading: "Reflection",
      paragraphs: [
        "Like most physical builds, the design phase is only half the story. It’s easy to make something look balanced and clean in a model, but once materials, weight, and real-world tolerances come into play, things rarely fit exactly as imagined. This reinforced the importance of thinking about assembly order, access, and how the structure will actually be handled during installation.",
        "If I were doing it again, I would spend more time considering how individual sections could be replaced or adjusted without affecting the whole structure. Timber outdoors will eventually deteriorate, and designing with maintenance in mind from the start makes future work simpler. The main lesson was that good design is not just about layout it’s about how something survives use over time."
      ]
  },
  "portfolioWebsite": {
    heading: "Reflection",
      paragraphs: [
        "Building the site without a framework was deliberate. I wanted to understand exactly how everything fit together instead of relying on abstractions. That decision gave me full control, but it also meant I had to be disciplined about structure. As more projects and loaders were added, it became clear how easily small pieces of logic can start overlapping if you don’t keep responsibilities clearly separated.",
        "The biggest lesson was about restraint. It’s easy to keep adding features and abstractions, but the more important challenge is keeping the system simple and readable. In future iterations, I would focus even more on consistency, reducing duplication earlier, and tightening the architecture before expanding it."
      ]
  },
  "quizCreator": {
    heading: "Reflection",
    paragraphs: [
      "This project worked well as an offline tool, but as the quiz content grew, the limitations of JSON became obvious. Large structured datasets inside a single file start to become harder to manage, especially when sections and relationships expand. In hindsight, separating content into smaller structured files or even using a lightweight database would have made the system easier to scale and maintain.",
      "The bigger lesson was about choosing the right storage layer for the problem. Spreadsheets made sense because they’re familiar and easy to edit, but once the structure is predefined and relationships matter, a database becomes a more natural fit. The tool works, but it also highlighted where a database backed version would be cleaner and more robust."
    ]
  },
  "thematic": {
    heading: "Reflection",
    paragraphs: [
      "While Excel made the system accessible and familiar, it also introduced structural limits. As themes, groupings, and relationships expanded, the JSON exports and linked data structures became increasingly complex. It worked, but the data relationships were already well defined, which makes it a strong candidate for a database driven approach instead of layered spreadsheets and JSON files.",
      "Databases are better suited for structured analysis and querying, especially when tools like PostgreSQL and analytics layers such as Superset can sit on top. The challenge is that initial data collection still needs to be simple, and most people are comfortable with spreadsheets. Going forward, a cleaner solution would likely involve structured data entry that feeds directly into a predefined database schema, reducing duplication and long-term complexity."
    ]
  },

  "dataAnalysisTool": {
    heading: "Reflection",
    paragraphs: [
      "This project began as an attempt to move beyond spreadsheet-based analysis tools and experiment with a structured database-driven approach. The system is built around a Docker environment running a Flask API and PostgreSQL database, with a small frontend used to explore database structure, relationships, and summary views.",
      "The project is still under development and not all planned features are fully implemented yet. The goal is to support structured data entry, summary configuration, and relationship inspection through the web interface, but parts of this workflow are still being refined. The work so far has mainly focused on building the architecture and modular API structure.",
      "One of the main motivations for this project came from the limitations encountered during the thematic analysis tool. As datasets and relationships grow, spreadsheet-based systems become harder to maintain and query. A database-backed approach allows the structure of the data to be defined once and then explored more flexibly.",
      "In the future I plan to expand the project into a more complete analysis environment by integrating tools such as Apache Superset for visualisation and exploration. The aim is to keep data entry simple while allowing more powerful querying and analysis once the data is stored in a properly structured database."
    ]
  },

  "powerShellCloudBackup": {
    heading: "Reflection",
      paragraphs: [
        "This tool exposed how easy it is to cause damage with automation if safeguards are not designed properly. Features like mirror mode are powerful, but they can delete data just as easily as they protect it. That forced me to build in confirmations, validation checks, and sync detection instead of assuming users would configure everything correctly.",
        "The main lesson was balancing flexibility with safety. Modular cloud providers and JSON configuration make it adaptable, but solid validation and clear warnings are what stop it doing something stupid. Automation should make things safer, not accidentally wipe your data."
      ]
  },
  "textCreator": {
    heading: "Reflection",
      paragraphs: [
        "Building this entirely offline was a deliberate constraint. It forced me to think about container boundaries, routing, and service orchestration without relying on external APIs. Docker simplified deployment, but it also required clear separation of responsibilities between frontend, model processing, and voice services.",
        "The biggest takeaway was that self hosted systems demand clarity. When everything runs locally, you are responsible for networking, performance, and failure handling. It reinforced the value of modular design and clean service boundaries."
      ]
  },
  "languageTranslator": {
    heading: "Reflection",
    paragraphs: [
      "This project reinforced how reusable UI components simplify expansion. By structuring the interface around modular panes and data attributes, adding additional languages became a matter of configuration rather than rewriting logic. That separation between structure and behavior kept the code manageable.",
      "Running translation and text to speech locally also highlighted the trade off between convenience and control. Self hosting removes external dependency, but it increases responsibility for configuration and performance. The lesson was to keep integration points simple and avoid unnecessary abstraction."
    ]
  },
  "promptForge": {
    heading: "Reflection",
    paragraphs: [
      "Prompt Forge grew out of the earlier text generator project, but it exposed a few weaknesses in how prompts were being written. Typing everything manually each time quickly became inconsistent, especially when trying to reuse the same structure across different tasks. The tool ended up being a way to experiment with breaking prompts into smaller components instead of treating them as a single block of text.",
      "Working on it also highlighted how easy it is for prompt systems to become overcomplicated. Some early ideas added too many fields and options, which made the interface harder to use rather than better. Simplifying the structure and keeping the components focused turned out to be the more practical approach."
    ]
  },
  "automationTools": {
    heading: "Reflection",
    paragraphs: [
      "The automation tools project came out of repeatedly setting up systems in roughly the same way and realising how easy it is to miss steps when doing it manually. The loader structure grew from trying to keep those tasks predictable instead of relying on memory or scattered scripts.",
      "While building it, it became obvious how quickly automation scripts can become messy if everything is mixed together. Separating configuration, validation, and execution made the tools easier to reason about. It also made it simpler to add new tools later without having to change the loader each time."
    ]
  },
  "testingTools": {
    heading: "Reflection",
    paragraphs: [
      "The testing tools project started from the small checks that come up when troubleshooting networks. Commands like scanning WiFi, checking neighbours, or testing ports are straightforward, but they usually involve jumping between several tools and remembering the right flags.",
      "Building a small framework around those checks made the process more consistent. It also showed that diagnostic tools do not need to be complicated to be useful. Simply organising common checks into a predictable structure makes troubleshooting easier when something is not working."
    ]
  },
  "vegeGardenBoxes": {
    heading: "Reflection",
    paragraphs: [
      "The planter boxes turned out strong and durable, but they were probably a bit overbuilt. At around 800mm high they required a large amount of soil to fill, which made the setup heavier and took quite a while to complete. If I built them again I would likely add internal supports or feet to reduce the volume of soil needed.",
      "Another improvement would be planning irrigation before filling the beds. Installing watering hoses or a simple irrigation line first would have made watering easier and saved some effort once the soil was already in place."
    ]
  },

  "verticalGreenhouse": {
    heading: "Reflection",
    paragraphs: [
      "Overall the vertical greenhouse worked well and achieved the goal of saving space while still allowing multiple plants to grow. The stacked layout made watering and access reasonably straightforward.",
      "One thing I would improve is how the plastic covering is installed. At the moment it is simply screwed directly to the frame. In future it would probably be better to build removable frames or panels so the plastic could be replaced more easily in sections if it wears out."
    ]
  }
};
