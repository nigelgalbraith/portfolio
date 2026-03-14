// JSON/mainTextData.js
// Static JavaScript object used as embedded content data for main content rendering

const MAIN_TEXT_DATA = {
  "home": {
  "paragraphs": [
    "I’m an IT professional based in Christchurch, New Zealand, with a broad background in infrastructure, networking, virtualization, and automation. I like putting together smart, practical solutions whether that’s for a workplace setup or one of my own DIY projects.",
    "I started out doing hands on trades work, then studied at Ara Institute of Canterbury where I got into IT. That mix of practical know how and new ideas still guides how I approach things today.",
    "For me, it’s always about problem solving and finding efficient ways to get things done. I reckon tech, when used right, can make life easier and a bit greener too.",
    "Feel free to have a look through the projects or get in touch if you'd like to talk about ideas, systems, or solving interesting problems."
  ]
  },
  "about": {
    "paragraphs": [
      "I'm Nigel Galbraith, an IT professional with a broad background in infrastructure, virtualization, and automation. I started out in trades before moving into tech, which gave me a practical way of looking at systems making sure they’re reliable, sustainable, and easy to use.",
      "I like tackling complex problems and finding efficient solutions. For me, tech works best when it’s practical, creative, and makes life easier."
    ]
  },
  "contact": {
      "paragraphs": [
          "Want to get in touch? Here are a few ways you can reach me.",
          "Send a message anytime, I’d be keen to hear from you."
      ],
      "lists": [
          {
          "items": [
              'Email: <a href="mailto:nigel.galbraith@proton.me">nigelgalbraith@proton.me</a>',
              'GitHub: <a href="https://github.com/nigelgalbraith/" rel="noopener" target="_blank">github.com/nigelgalbraith</a>',
              'LinkedIn: <a href="https://www.linkedin.com/in/nigel-galbraith" rel="noopener" target="_blank">linkedin.com/in/nigel-galbraith</a>'
          ]
          }
      ]
  },
  "arcadeCabinet": {
    "paragraphs": [
      "For this project, I built a custom MAME arcade cabinet using waste MDF and salvaged timber from my joinery work, giving new life to materials that would have otherwise been discarded. The cabinet was designed from scratch and cut using basic woodworking tools, with a focus on keeping costs low but also maintain an authentic retro look and feel.",
      "I integrated an i PAC circuit board to handle keyboard inputs from real arcade buttons and joysticks, giving the experience a true arcade feel.",
      "It runs Windows with HyperSpin as the front end interface, supporting a library of over 4,000 classic games from various consoles and arcade systems. The build was a great way to combine my interest in retro gaming with hands on woodworking and hardware integration skills."
    ]
  },
  "greenhouseBoxes": {
    "paragraphs":
    [
      "I designed a set of planter box layouts in SketchUp, trying out different ways to get the most growing space while still keeping access easy. The idea was to keep it modular so it could be put together in the greenhouse without too much hassle. I used reclaimed wood where I could, and added galvanized screws at the corners to keep it solid.",
      "Using SketchUp gave me a chance to work through different layouts before I started building, which saved time and cut down on mistakes. It also helped me show the plan more clearly, so everyone could picture how it would fit together in the greenhouse."
    ]
  },
  "kvmLab": {
    "paragraphs": [
      "The KVM Student Labs project replaced VMware Workstation Pro with an open source stack built on Ubuntu, QEMU, and Libvirt. The goal was to reduce licensing costs, improve performance, and introduce domain-based authentication for managing student virtual machines.",
      "Integrating the Linux host with Active Directory and ensuring hardware compatibility was more involved than expected. Limitations in the test environment slowed progress and forced adjustments to the original plan. This shifted the focus toward feasibility testing, reproducible setup steps, and stronger documentation."
    ]
  },
  "sharepointGps": {
    "paragraphs": [
      "At Downer, I developed a SharePoint-based system to improve communication and coordination within the traffic management team.",
      "The platform centralised Traffic Management Plans (TMPs), site checks, and planning tools into one accessible location.",
      "It reduced paperwork and improved visibility between field crews and office staff, while highlighting the practical challenges of deploying digital systems in real-world conditions."
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
  "terraceGardens": {
    "paragraphs": [
      "I designed terrace gardens in SketchUp, trying out different planter box layouts and levels to get a setup that was simple and balanced. The idea was to keep the build straightforward and modular, using reclaimed wood and solid fixings to make it durable but still easy to put together.",
      "For me it’s about using tech to save time and make the hands on work easier. SketchUp lets me try different options before building, and it also helps when explaining ideas to others. Having a model to look at means everyone can see the same thing and be clear on how it should come together."
    ]
  },
  "portfolioWebsite": {
    "paragraphs": [
      "Here I’ve documented how I put together my portfolio site, from the folder layout to the JavaScript that runs it. I set it up to be modular and easy to maintain, without using frameworks.",
      "The pages are static HTML with styling and behavior handled by reusable JavaScript modules. Content gets pulled into templates, which keeps things simple to update and avoids repeating code. Each project has its own page, and loaders take care of things like images and footers.",
      "The setup keeps structure (HTML), style (CSS), and behavior (JS) clearly separated. Building it from scratch gave me full control over layout, accessibility, and performance, while also giving me the chance to teach myself new skills along the way."
    ]
  },
  "quizCreator": {
    "paragraphs": [
      "This project is a self contained quiz generator that takes questions, answers, and explanations from a structured Excel spreadsheet and turns them into an interactive web quiz.",
      "I built it as a simple offline tool no sign ups, no third party platforms, and no need for internet access. Being able to create and run quizzes locally makes it handy for personal study, classrooms, or places with limited connectivity.",
      "Repetition and practice were key to how I learned during my study. This project let me build quizzes tailored to my own pace and topics, so I could reinforce concepts and revisit areas as often as needed.",
      "The current version is based on CyberOps content, but the setup is flexible. Swap out the spreadsheet and it can be used for IT, science, languages, or any subject.",
      "It was also a way to put my skills into practice using Python and pandas for data handling, Excel integration, and web tech like HTML, JavaScript, and JSON to build the quiz interface. The focus was on keeping it easy to use and practical."
    ]
  },
  "thematic": {
    "paragraphs": [
      "This project streamlines thematic analysis by combining structured Excel sheets with automated data handling and web export tools. It takes a task that’s usually repetitive and time consuming and makes it faster and more organised.",
      "I built it to cut down on manual work no endless copying, pasting, or cross referencing. With macros and structured workflows, it keeps the analysis consistent and makes sure factors, groupings, and categories are properly tracked.",
      "When I worked with qualitative datasets, I found it easy to get lost managing themes and metadata. This system gave me a clearer, repeatable process, letting me focus more on the insights instead of fixing formulas or formatting.",
      "The results can be exported to a web format, so findings are easier to review and navigate. It also builds glossaries, group relationships, and simple risk model automatically, making easier to understand.",
      "It was a chance to apply what I’ve been learning Excel automation, Python scripting, and front end web development. It’s flexible enough to handle different types of thematic work, from research to education or internal reporting."
    ]
  },
  "powerShellCloudBackup": {
      "paragraphs": [
      "This tool backs up selected files and folders to cloud storage like Google Drive, Dropbox, or Mega NZ before shutdown or logoff. You can choose between zipped backups (with retention) or raw file copies in append or mirror mode. It includes customizable settings, a GUI for configuration, and checks to confirm sync is complete.",
      "Even though it’s been tested, I recommend running a manual backup first to avoid data loss. This matters most in 'Mirror' mode, which can delete files in the destination to match the source. Always double check your paths and settings before using automatic shutdown.",
      "Most cloud providers, including Google Drive, Dropbox, and Mega NZ, keep deleted files for a short time (usually up to 30 days), which can help recover mistakes. Still, it’s best to set things up carefully from the start.",
      "Backup settings are stored in editable JSON files, so you can update preferences without touching the script. You can also add new cloud providers by extending the `cloudProviders.json` file with another provider block."
    ]
  },
  "debianInstallSuite": {
    "paragraphs": [
      "This set of Python and Bash scripts automates the setup of Debian based systems using a modular, model aware design. Each script handles a specific task like installing packages, setting firewall rules, configuring RDP, deploying services, or managing third party repos. All behavior is driven by JSON config files linked to system models, making the tool flexible across different environments.",
      "The scripts follow a simple flow: detect the system model, load the right config, validate input, run the job, and log everything to a versioned logs directory. Each installer asks for confirmation before changes are made, and logs are rotated automatically to keep things tidy.",
      "Instead of maintaining one standard image, the scripts let you define rules per device type and apply them with a single command.",
      "Core logic is split into utility modules for logging, service setup, file permissions, JSON parsing, and more. This makes them easy to extend and maintain, with room to grow into GUI tools, remote execution, or Ansible style automation later on."
      ]
    },
  "textCreator": {
    "paragraphs": [
      "This project is a standalone text generator built to run entirely offline using Ollama and Piper. I wanted a tool that was simple, fast, and private, without relying on any external services or cloud APIs. Everything is handled locally through Docker containers, with the frontend served by Nginx and the model processing done through a JavaScript interface.",
      "The system loads a profile file, builds dynamic form fields and checklists, and then sends the structured prompt to the LLM to generate text. It also includes a profile builder so you can design your own templates, styles, and metadata without editing the JSON manually.",
      "A built-in text-to-speech option runs through Piper, letting the tool read the generated text out loud using a local voice model. The whole setup focuses on practicality and ease of use: clean layouts, modular panes, no frameworks, and everything bundled into a Docker compose file so it can be deployed on any machine with a single command."
    ]
  },
  "languageTranslator": {
    "paragraphs": [
      "This project is a self hosted language translator that combines LibreTranslate with Piper text to speech. It runs entirely in Docker, with Nginx serving the frontend and proxying clean routes to the translation and voice services. Everything stays local, with no external cloud APIs.",
      "The main menu lets you choose between Spanish and Chinese, each with a dedicated page for both directions of translation. The UI is built from small reusable panes for text entry, translation previews, toggle buttons, and audio playback. Each lane is wired with data attributes, so the same JavaScript modules can drive both languages.",
      "LibreTranslate handles the actual translation, while three Piper instances provide natural voices for English, Spanish, and Chinese. Nginx exposes simple endpoints for /translate and the per language TTS services, keeping the browser code straightforward and easy to follow."
    ]
  },
  "promptForge": {
    "paragraphs": [
      "Prompt Forge is a web based prompt workstation built to run locally with Docker. It expands on the earlier Text Creator idea by moving the workflow into a browser interface, while still keeping everything simple, private, and easy to manage on your own machine.",
      "The frontend is served through Nginx and uses vanilla JavaScript modules, while a lightweight Node and Express API handles prompt generation requests and saved profile management. Profiles can be created, edited, stored as JSON, and loaded back into the interface, which makes it easier to reuse structured prompt setups without rebuilding them each time.",
      "The system is designed to work with local providers like Ollama and LocalAI, with optional Piper text to speech support as part of the wider setup. The focus was on keeping the tool practical and modular: no heavy frameworks, no cloud dependency, and a clean split between the browser UI, API layer, and local model services."
    ]
  },
  "automationTools": {
    "paragraphs": [
      "This project is a modular automation framework built around a single loader and a structured pipeline system. Instead of writing one off scripts for each task, I wanted a cleaner way to define tools through constants modules, config files, validation rules, and reusable execution states.",
      "The loader handles the common work: checking dependencies, loading JSON config, validating structure, showing documentation, building menus, and then running the selected action through an ordered pipeline. That keeps the tool specific logic out of the loader itself and makes it easier to extend without turning the project into a mess.",
      "At the moment the framework is set up around a Text Creator style workflow, but the main point is the architecture rather than one specific tool. It was built to support repeatable terminal based automation in a way that stays predictable, maintainable, and easy to grow into other utilities later."
    ]
  },
  "testingTools": {
    "paragraphs": [
      "This project applies the same loader based architecture to a set of terminal testing and diagnostic tools. Rather than building separate stand alone scripts, I used a shared tool loader and pipeline style state machine so the utilities follow the same structure for setup, validation, selection, and execution.",
      "The current tools include a Wi Fi scanner and a network scanner. They can list interfaces, scan for nearby wireless networks, inspect selected network details, show ARP neighbours, and run TCP port scans against chosen hosts. Each tool has its own config, documentation, and constants module, while the shared modules handle the common execution flow.",
      "The main goal was to keep the tools modular and predictable while still being useful for real troubleshooting. It shows how the same framework can be reused in a different area, taking the loader idea beyond automation tasks and applying it to practical network testing work."
    ]
  },
  "vegeGardenBoxes": {
    "paragraphs": [
      "I built these raised vegetable garden boxes to make growing food easier without having to bend down all the time. The extra height makes planting, watering, and harvesting much easier on the back.",
      "The boxes were designed with cost and durability in mind. I used corrugated iron for the sides because it lasts much longer than untreated timber and holds up well outdoors. The goal was to build something solid without spending a lot of money.",
      "Before building, I used SketchUp to experiment with the layout and proportions. Modelling the boxes first helped work out dimensions and spacing so the final build came together more smoothly."
    ]
  },
  "verticalGreenhouse": {
    "paragraphs": [
      "This project explores a vertical greenhouse layout designed to save space while still allowing a good number of plants to be grown. Instead of spreading out across the ground, the growing trays are stacked vertically to make better use of the available area.",
      "The stacked drawer style layout also makes watering easier, as each level can be accessed from the front. This keeps the setup compact while still being practical to maintain.",
      "Through experimenting with materials, I found timber held up better than plastic in the greenhouse environment. Plastic trays tended to become brittle from the heat over time, while metal could potentially heat up too much. Using wood provided a good balance of durability and stability for the structure."
    ]
  },
};
