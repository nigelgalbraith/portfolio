// js/JSON/projectSteps.js

const ProjectSteps = {
// Step-by-step breakdown for the Thematic Analysis project
thematic: [
    {
    title: "Thematic Analysis Structure and Relationships",
    img: "ThematicAnalysisStructureEDR.png",
    alt: "Thematic Analysis Structure and Relationships",
    text: "This project uses a structured workflow to transform raw text into meaningful insights. At its core, the thematic analysis links Extracts (raw data) to Factors (identified themes), which are then grouped into Groups, Sub-Groups, and categorized further. This structured hierarchy allows for powerful visualizations, risk models, and filtering in the final web output.The process begins in Excel, where users record and classify data. A Python script converts the workbook into structured JSON, enabling dynamic exploration on the final webpages"
  },
  {
    title: "Step 1: Enter Extracts and Identify Factors",
    img: "ThematicAnalysisIntial.png",
    alt: "Entering Extracts and Factors",
    text: "Begin by collecting qualitative data such as participant quotes, observations, or written feedback. Each distinct segment, referred to as an 'extract,' is entered into the Excel workbook. Alongside each extract, note any recurring themes, patterns, or ideas, which are captured as individual 'factors.' If you are entering a factor manually, first set the mode to 'Manual' to avoid duplication caused by the macro. Once factors are added to the glossary table, they become available for selection via the drop-down list at that point, switch the mode back to 'List' to enable structured selection and maintain consistency. If you need to edit or delete specific factors later, switch to 'Manual' mode before making changes to ensure smooth editing without macro interference."
  },
  {
    title: "Step 2: View Identified Factors",
    img: "FactorInput.png",
    alt: "Viewing Factors",
    text: "After populating the initial extract and factor fields, the built-in Excel macro provides a consolidated view of all identified factors. This is a chance to catch spelling inconsistencies, repeated entries, or missing values. By reviewing this list before progressing, you ensure the thematic framework has integrity and reduces downstream confusion."
  },
  {
    title: "Step 3: Populate the Glossary Table",
    img: "PopulateGlossary.png",
    alt: "Glossary Table",
    text: "The glossary serves as a thematic map. Here, each factor is assigned to broader Groups and Sub-Groups. This classification adds structure and makes it easier to interpret patterns at scale. Instead of viewing factors in isolation, the glossary helps relate them to higher-level themes, aiding both clarity and usability in the final web output."
  },
  {
    title: "Step 4. Assign Group and Sub-Group Values",
    img: "UpdateGroupSubGroup.png",
    alt: "Group and Sub-Group Update",
    text: "Return to the Thematic Analysis sheet and click the 'Update Group' and 'Update Sub Group' buttons. These will populate the appropriate values from your Glossary Table. If you also need to edit factor entries manually such as updating or deleting values be sure to switch the mode to 'Manual' first to prevent duplication or conflicts caused by the macro. Once editing is complete, switch back to 'List' mode to resume structured selection. The sheet highlights missing factors from the glossary in red, providing quick visual feedback if anything is incomplete."
  },
  {
    title: "Step 5. Refresh the Search Tool Dataset",
    img: "UpdateSearchTool.png",
    alt: "Search Tool Data",
    text: "This step pulls everything together. Run the update function to copy all the finalized factors and their assignments into the Search Tool Data sheet. This dataset powers the dropdown filters and logic behind the web-based search tool, so keeping it up to date ensures accurate results later on."
  },
  {
    title: "Step 6. Define Categories and Sub-Categories",
    img: "UpdateCatSubCat.png",
    alt: "Finalizing Categories",
    text: "Add or review the Category and Sub-Category tags for each factor. You can use the buttons to automatically fill these in from the Glossary Table. Add new rows if you've introduced additional themes during your review. This structure helps support advanced filtering and future reporting."
  },
  {
    title: "Step 7. Export for Web Use",
    img: "TAWebUpdateFlow.png",
    alt: "Exporting Thematic Analysis",
    text: "Once everything looks good, save the workbook as 'Thematic-Analysis-Complete.xlsm'. Then run the 'Python-Update-Webpage.py' script from the Python-Import folder. This script turns your structured Excel data into JSON and HTML, which power the interactive web pages for analysis and search."
  },
  {
    title: "Site HTML Structure Overview",
    img: "ThematicAnalysisHTMLStructure.png",
    alt: "Thematic Analysis HTML Page Structure",
    text: "This diagram illustrates the overall structure of the HTML pages in the thematic analysis tool. Each page serves a specific purpose in presenting analysis results, grouped content, and detailed views. Understanding this structure helps clarify how your exported data connects to the interface."
  },
  {
    title: "Excel to JSON Conversion",
    img: "TAImportFlow.png",
    alt: "Excel Data Import Output",
    text: "This utility extracts data from structured Excel sheets and exports it to JSON format. Using a configurable dictionary, it maps sheet names and starting rows to output paths. This ensures consistent data formatting across the Tool Data, Thematic Analysis, and Risk Matrix sources."
  },
  {
    title: "Data Cleaning",
    img: "TACleanFlow.png",
    alt: "Python Clean Flow",
    text: "This Python script loads raw thematic data from multiple JSON files, cleans unwanted characters, restructures nested fields, and groups related records together. It then saves the cleaned output in both raw and JavaScript-ready formats."
  },
  {
    title: "JavaScript and Data Flow Structure",
    img: "ThematicAnalysisJSPages.png",
    alt: "Thematic Analysis JavaScript and JSON Relationships",
    text: "Once data is exported to JSON, a set of JavaScript modules process and display it within each page. This diagram shows the relationships between the various scripts (`intGroupAnalysis.js`, `RiskMatrix.js`, etc.) and their associated data files. It helps make sense of how your thematic structure is rendered dynamically across the site."
  },
  {
    title: "Search Tool JavaScript and Data Flow",
    img: "SearchToolHTMLStructure.png",
    alt: "Search Tool Site Map",
    text: "This diagram illustrates the simplified structure of the Search Tool interface. It shows how the main HTML page (`Index.html`) connects to key JavaScript controllers (`initSearchTool.js`, `SearchTool.js`) and the underlying dataset (`toolJSON.js`). This clear separation makes it easier to understand the flow from page initialization to data filtering logic."
  },
  {
    title: "Step 8. Use the Search Tool Webpage",
    img: "WebSearchTool.png",
    alt: "Search Tool Output",
    text: "With the export complete, you can now explore your data through the interactive Search Tool. Use the dropdowns to filter by Category, Sub-Category, Group, or Sub-Group. It also includes a glossary and full factor list, making it easy to locate key themes and track their source."
  },
  {
    title: "Step 9. Review the Thematic Analysis Web Output",
    img: "ThematicWebResults.png",
    alt: "Thematic Analysis Output",
    text: "This page lays out your entire thematic structure visually. You’ll see Groups, their linked Factors, and the Extracts they were drawn from. Depending on the data, you might also see visual metrics like risk levels or frequency scores. It’s a great way to step back and get a full-picture view."
  },
  {
    title: "Groupings Overview",
    img: "GroupingsWeb.png",
    alt: "Thematic Analysis Groupings Output",
    text: "This visualization shows how factors are grouped into broader themes. It’s a quick way to see where patterns are forming and which areas are more densely populated. Ideal for finding common threads or comparing thematic clusters across the dataset."
  },
  {
    title: "Factor-Level Analysis",
    img: "FactorAnalysisWeb.png",
    alt: "Thematic Analysis Factor Analysis Output",
    text: "Dive into each factor to see how often it appears, what context it's used in, and which themes it supports. This helps surface which ideas are most influential, underused, or worth following up on. Great for prioritising themes or backing up decisions with data."
  },
  {
    title: "Group-Level Analysis",
    img: "GroupAnalysisWeb.png",
    alt: "Thematic Analysis Group Analysis Output",
    text: "This breakdown shows the size, spread, and relative weight of each Group. You can compare how often each theme is mentioned and how it connects to others. It’s helpful when you want to identify dominant topics or check for gaps in coverage."
  },
  {
    title: "Sub-Group Analysis",
    img: "SubGroupAnalysisWeb.png",
    alt: "Thematic Analysis Sub Group Analysis Output",
    text: "Takes you deeper into the smaller, more focused themes within each Group. Sub-Groups can highlight niche concerns, outliers, or specific issues tied to a broader topic. Use this when you need to fine-tune your insights or tailor your findings to a specific audience."
  },
  {
    title: "Risk Model Creator",
    img: "RiskModelCreatorWeb.png",
    alt: "Thematic Analysis Risk Model Creator Output",
    text: "This tool lets you build custom risk models based on the grouped factors. You can define scenarios, assign risk levels, and visually map out how different themes impact potential outcomes. It's especially useful if you’re turning qualitative data into action plans or dashboards."
  }
  ],

  // Step-by-step breakdown for the quiz creator project
  quiz: [
  {
    title: "Quiz Creator System Overview",
    img: "QuizCreatorStructure.png",
    alt: "Quiz Creator Site Map",
    text: "This diagram shows the structure of the quiz system. The HTML pages load the core JavaScript modules, which in turn access a shared JSON file for all quiz data. This clear separation of structure, logic, and content allows for flexible updates and easy maintenance."
  },
  {
    title: "Step 1: Add Custom Questions and Answers",
    img: "QuizCreatorScreenShot-Excel.png",
    alt: "Quiz",
    text: "Start by entering your quiz content into the Excel workbook. Each row includes a question, multiple choice answers, the correct answer, and a short explanation. This layout gives you flexibility to define your own topics and maintain consistent formatting across all quizzes."
  },
  {
    title: "Step 2: Quiz: Update the Webpage Content",
    img: "quizWebUpdateFlow.png",
    alt: "Quiz Python Program Flow Chart",
    text: "Once your spreadsheet is finalised, run the 'Python-Update-Webpage.py' script from the Python-Import folder. This script updates the quiz content by extracting data from the Excel workbook, formatting it, and saving new HTML and JSON files used by the quiz interface."
  },
  {
    title: "Excel to Quiz JSON Import",
    img: "QuizImportFlow.png",
    alt: "Quiz Excel Import",
    text: "This stage reads the structured Excel file and combines all the module sheets into a single JSON file. Each sheet's questions, answers, and metadata are converted to structured records. This ensures all quiz content is accurately captured before it's cleaned or displayed."
  },
  {
    title: "Quiz Data Cleaning and Script Injection",
    img: "QuizCleanFlow.png",
    alt: "Quiz Cleaning and Injection",
    text: "Once the raw JSON is created, this stage cleans and restructures the data. It splits fields like 'Multiple Answers', groups them by module, and wraps the result in a JavaScript variable. This output is injected into the quiz interface, ready for live use."
  },
  {
    title: "Step 3: Launch the Quiz Selector",
    img: "QuizCreatorScreenShot-QuizIndex.png",
    alt: "Quiz Main Page",
    text: "Open the index.html file to launch the quiz selector page. From here, users can choose which quiz to take. Each quiz is linked to the dataset you defined in the Excel workbook, allowing for quick testing and review."
  },
  {
    title: "Step 4: Submit and Check Your Answers",
    img: "QuizCreatorScreenShot-QuizPostAns.png",
    alt: "Quiz Question Check",
    text: "As users complete the quiz, they can click 'Submit' after each question to receive instant feedback. The app highlights the correct answer and provides a brief explanation, making it useful for both practice and reinforcement."
  },
  {
    title: "Step 5: Review the Quiz Summary",
    img: "QuizCreatorScreenShot-QuizRedsults.png",
    alt: "Quiz Results",
    text: "After completing all the questions, clicking 'Submit Quiz' will generate a summary of the user’s performance. This includes the number of correct answers, a list of incorrect responses, and links to explanations for review."
  },
  {
    title: "Step 6: Build and Load Custom Quizzes",
    img: "QuizCreatorScreenShot-QuizExcelSheetDefine.png",
    alt: "Quiz ExcelSheet Definition",
    text: "While the default quizzes use CyberOps examples, you can easily adapt the tool for other topics. Just create a new Excel file using the same structure, then update the path in the 'import-Tool-Data.py' script to point to your new file. The rest of the system will adapt automatically."
  }
  ],
  // Step-by-step breakdown for the Website project
  portfolio: [
    {
    title: "HTML Architecture Plan",
    text: "I began by mapping out the HTML structure of the site — deciding on core pages (like About, Resume, Projects), and how they would be linked together. This gave me a clear navigation flow and helped identify which project pages would sit underneath the main Projects page. Planning this first made it easier to keep internal linking and layout consistent.",
    img: "SiteHTMLStructure.png",
    alt: "Diagram showing how the main HTML pages and project subpages are connected"
    },
    {
    title: "JavaScript Architecture (Main Pages)",
    text: "To keep things modular, I mapped out which JavaScript files are loaded by each HTML page. For example, the Resume page loads `resumeLoader.js` and `skillsLoader.js`, which in turn pull in data like `resumeData.js` and `skills.json`. Each file is focused on a single job, making the system easy to maintain.",
    img: "SiteJSMainPages.png",
    alt: "Diagram showing JavaScript modules and data linked to the Home and Resume pages"
    },
    {
    title: "JavaScript Architecture (Project Pages)",
    text: "The Projects page has its own set of modular JavaScript files, such as `projectListLoader.js`, `carousel.js`, and `embedSketchfab.js`. Each of these loads specific data (like project steps or Sketchfab models) only when needed. This structure ensures better performance and easier updates as more features are added.",
    img: "SiteJSProjectPages.png",
    alt: "Diagram showing JavaScript loaders and JSON data modules for the Projects page"
    },
    {
      title: "projectListLoader.js",
      text: "This script dynamically builds the list of projects shown on the Projects page. It loads an array of project entries from `projectListData.js`, then loops through them to create styled DOM cards for each project. These cards include images, titles, and tags, making the list easy to maintain and update with new work.",
      img: "projectListLoaderFlow.png",
      alt: "Flowchart showing how projectListLoader.js reads data and builds cards"
    },
    {
      title: "githubAppLoader.js",
      text: "This script loads playable GitHub-hosted apps into the Projects page. It reads a list of apps from `githubApps.js`, creates iframe elements for each one, and inserts them into the DOM. This modular approach makes it easy to add or remove playable demos without editing HTML directly.",
      img: "githubAppLoaderFlow.png",
      alt: "Flowchart showing how GitHub app iframes are built and injected"
    },
    {
      title: "embedSketchfab.js",
      text: "This module integrates 3D models into project pages using Sketchfab embeds. It loads model info from `sketchfabModels.js`, creates iframe elements with correct configuration, and injects them where needed. This allows interactive model previews without overloading the page.",
      img: "embedSketchfabFlow.png",
      alt: "Flowchart showing the loading and embedding process for Sketchfab models"
    },
    {
      title: "projectStepsData.js",
      text: "Used to walk through project processes, this script loads structured steps from `projectSteps.js` and renders them as expandable sections. It’s ideal for tutorials or detailed walkthroughs, keeping each step clearly separated and easy to follow.",
      img: "projectStepsDataFlow.png",
      alt: "Flowchart showing how step data is loaded and displayed"
    },
    {
      title: "projectLinksLoader.js",
      text: "This module reads link definitions from `projectLinks.js` and builds buttons like 'Live Demo' or 'View Code' dynamically. It keeps call-to-action buttons consistent and ensures they always match the associated project.",
      img: "projectLinksLoaderFlow.png",
      alt: "Flowchart showing how external project links are injected"
    },
    {
      title: "carousel.js",
      text: "This script builds a responsive image carousel from data in `carouselData.js`. It generates slide elements, sets up left/right navigation, and handles auto-advance. Great for previewing multiple screenshots in a compact space.",
      img: "carouselFlow.png",
      alt: "Flowchart showing how carousel images are loaded and rotated"
    },
    {
      title: "modalZoom.js",
      text: "When users click on a media item (image or model), this script opens a modal for an enlarged view. It improves accessibility and allows users to explore fine details without leaving the page.",
      img: "modalZoomFlow.png",
      alt: "Flowchart showing modal activation and image zoom"
    },
    {
      title: "init.js",
      text: "This file acts as a coordinator for the Projects page. Once the DOM is ready, it triggers all related loaders like `projectListLoader`, `embedSketchfab`, and others, ensuring that everything loads in the right order.",
      img: "initFlow.png",
      alt: "Flowchart showing how scripts are initialized in sequence"
    },
    {
      title: "menuToggle.js",
      text: "This script handles mobile navigation. It toggles a class on the site’s menu when the user taps the hamburger icon, allowing the menu to expand or collapse on small screens.",
      img: "menuToggleFlow.png",
      alt: "Flowchart showing how the menu is shown and hidden"
    },
    {
      title: "mainTextLoader.js",
      text: "This script loads homepage intro text from `mainTextData.js`, formats it, and inserts it into the DOM. It keeps the homepage content flexible and editable from a single data file.",
      img: "mainTextLoaderFlow.png",
      alt: "Flowchart showing how the homepage intro text is populated"
    },
    {
      title: "footerIconLoader.js",
      text: "This script reads icon entries from `iconRegistry.js` and generates the clickable icons in the site footer (e.g., GitHub, LinkedIn). It ensures consistent styling and makes it easy to update links globally.",
      img: "footerIconLoaderFlow.png",
      alt: "Flowchart showing how footer icons are built and inserted"
    },
    {
      title: "responsiveImageLoader.js",
      text: "To improve performance, this script checks screen width and selects the best image resolution for the device. It helps avoid loading large images on mobile and makes sure visuals stay sharp.",
      img: "responsiveImageLoaderFlow.png",
      alt: "Flowchart showing image resolution selection and loading"
    },
    {
      title: "resumeLoader.js",
      text: "This script builds the timeline on the Resume page using data from `resumeData.js`. It loops through jobs, roles, and dates, and formats them into vertical entries that are easy to read.",
      img: "resumeLoaderFlow.png",
      alt: "Flowchart showing how resume entries are rendered"
    },
    {
      title: "skillsLoader.js",
      text: "Loads the skill set from `skillsData.js`, and creates icons, labels, or badges for each one. Skills are sorted into categories and displayed responsively so they look good on any screen size.",
      img: "skillsLoaderFlow.png",
      alt: "Flowchart showing how skills data is visualized"
    },
    {
      title: "Generate-SiteDiagrams.py",
      text: "This Python script generates Mermaid diagrams for HTML and JavaScript structure. It loads site layout from JSON, writes `.mmd` syntax, and uses the Mermaid CLI to export `.svg` and `.png` diagrams used in the Portfolio.",
      img: "GenerateSiteDiagramsFlow.png",
      alt: "Flowchart showing how the Mermaid site diagrams are generated"
    },
    {
      title: "Image-Optimizer.py",
      text: "This tool resizes images into multiple screen-specific sizes (desktop, laptop, mobile) and compresses thumbnails and icons. It keeps the site fast while maintaining quality visuals.",
      img: "ImageOptimizerFlow.png",
      alt: "Flowchart showing how images are processed for different screen sizes"
    },
    {
      title: "Generate-Flowchart.py",
      text: "This program reads node and connection definitions from JSON files and creates styled flowcharts using Graphviz. It's used to explain the logic of each JavaScript or Python module visually.",
      img: "GenerateFlowchartFlow.png",
      alt: "Flowchart showing how flowchart PNGs are generated from JSON"
    }
  ],
  // Step-by-step breakdown for the PowerShell Backup Tool
  powerShellCloudBackup: [
    {
      title: "Backup Tool Project Structure",
      img: "BackupStructure.png",
      alt: "Backup Tool File Structure",
      text: "This diagram outlines how the main PowerShell script connects with its supporting modules and configuration files. Each file is responsible for a distinct part of the workflow, allowing for a modular and maintainable architecture. The configuration files (like cloudProviders.json and mainConfig.json) are easy to edit manually, enabling you to customize layout, backup defaults, or even add support for new cloud providers without modifying the script itself."
    },
    {
      title: "Step 1: Launch the Tool",
      img: "BackupLaunch.png",
      alt: "Launching Backup Tool",
      text: "To begin, either run the `main.ps1` script in PowerShell or double-click the included `.bat` file. This launches the user-friendly GUI and loads your previous settings, if available."
    },
    {
      title: "Step 2: Configure Source and Destination",
      img: "BackupSourceDest.png",
      alt: "Selecting Source and Destination",
      text: "Use the 'Browse' buttons to pick the folders you want to back up and the cloud destination where files should go. Each provider (Google, Dropbox, Mega) has its own tab."
    },
    {
      title: "Step 3: Choose File Copy Mode (Robocopy)",
      img: "BackupModeRobocopy.png",
      alt: "Choosing File Copy Mode",
      text: "If you select File Copy as your backup method, you can choose between Append and Mirror mode. 'Append' will add new or changed files to the destination, keeping everything already there. 'Mirror' will make the destination exactly match the source including deleting files that no longer exist in the source folder."
    },
    {
      title: "Step 4: Choose Zip Archive Mode",
      img: "BackupModeZip.png",
      alt: "Choosing Zip Backup Mode",
      text: "If you select Zip Backup, the tool will compress your source files into a timestamped archive. You can choose how often to create a zip (Daily, Weekly, Monthly) and how many previous zip files to retain. This is useful for versioned backups or archival snapshots."
    },
    {
      title: "Step 5: Run Backup or Shutdown",
      img: "BackupButtons.png",
      alt: "Performing Backup",
      text: "Once your settings are configured, click 'Backup' to begin the process. Choosing 'Backup + Shutdown' attempts to wait for cloud sync to complete before powering off. However, depending on your system and cloud provider, the tool may sometimes shut down too early or briefly stop responding while waiting. These issues are under active improvement. If you're unsure whether syncing has finished, it's safer to run a manual 'Backup' first and shut down afterward."
    },
    {
      title: "main.ps1 Flowchart",
      img: "BackupMainPS1Flow.png",
      alt: "Flowchart of main.ps1",
      text: "This flowchart shows how the main script handles config loading, GUI setup, and user actions like backup or shutdown. It serves as the entry point of the entire tool."
    },
    {
      title: "BackupConfig.psm1 Flowchart",
      img: "BackupConfigFlow.png",
      alt: "Flowchart of BackupConfig.psm1",
      text: "Responsible for loading global settings, font styles, control layout, and application-wide parameters from `mainConfig.json` and related files."
    },
    {
      title: "BackupCore.psm1 Flowchart",
      img: "BackupCoreFlow.png",
      alt: "Flowchart of BackupCore.psm1",
      text: "This module runs the actual backup logic. It validates paths, performs file or zip operations, checks for sync status, and logs the results."
    },
    {
      title: "BackupUI.psm1 Flowchart",
      img: "BackupUIFlow.png",
      alt: "Flowchart of BackupUI.psm1",
      text: "Creates the GUI tabs, file selection fields, and buttons. It handles layout and event bindings to ensure user actions are captured correctly."
    },
    {
      title: "FileSystemUI.psm1 Flowchart",
      img: "BackupFileSystemUIFlow.png",
      alt: "Flowchart of FileSystemUI.psm1",
      text: "This module builds the advanced tree-view picker for selecting multiple source folders. It also manages how those paths are passed back to the main form."
    },
    {
      title: "Step 6: Review the Log",
      img: "BackupLogOutput.png",
      alt: "Backup Log Output",
      text: "After the backup completes, review the on-screen log for results, errors, or skipped files. This feedback confirms that all selected files were processed correctly. A copy of each log is also saved to your home directory under the 'logs' folder, so you can refer back to previous backups even after restarting the program."
    },
  ],
  // Step-by-step breakdown for the Debian Install
  debianInstallSuite: [
    {
      title: "Debian Setup Suite Structure",
      img: "DebianSuiteStructure.png",
      alt: "Debian Configuration Flow Diagram",
      text: "This diagram illustrates how the Debian setup process flows from a unified main script and model selector (`AppConfig`) into system-specific configurations. The AppConfig file determines the target model (Desktop, MediaCentre, or Laptop), and each model links to its own configuration file. This modular structure enables a scalable, repeatable setup process tailored to different system types using centralized logic and clean separation of concerns."
    },
    {
      title: "Step 1: Detect Model and Load Config",
      img: "DebianDetectModel.png",
      alt: "Model Detection and Config Loading",
      text: "Each script begins by checking the current hardware model (like 'ThinkPadX1' or 'OptiPlex7000') and loads the corresponding JSON config block. This allows tailoring the install to specific systems while maintaining a central source of truth in `AppConfigSettings.json`."
    },
    {
      title: "Step 2: Choose Install or Uninstall",
      img: "DebianInstallOptions.png",
      alt: "Install or Uninstall Menu",
      text: "The CLI prompts users to install or remove applications. Installers like `DebianPackageInstalls.py`, `DebianDebInstalls.py`, and `DebianFlatPakInstalls.py` filter packages based on current system state, avoiding unnecessary reinstalls or removals."
    },
    {
      title: "Step 3: Perform Jobs and Log Output",
      img: "DebianLoggingFlow.png",
      alt: "Logging and Execution",
      text: "Each installer logs its actions to a timestamped log file under a dedicated subdirectory (e.g., `logs/deb/`, `logs/services/`). Scripts also rotate logs automatically and print status summaries, making it easy to review success/failure outcomes after execution."
    },
    {
      title: "DebianRDP Bash Installer",
      img: "DebianRDPFlow.png",
      alt: "XRDP and XFCE Setup Flow",
      text: "The Bash script `DebianRDP.bash` installs and configures XRDP with XFCE for remote access. It checks required packages, sets up user sessions, and configures systemd services. You can also use it to uninstall XRDP or create new sudo users interactively."
    },
    {
      title: "Firewall Rules per Model",
      img: "DebianFirewallFlow.png",
      alt: "Firewall Configuration Logic",
      text: "`DebianSetFirewall.py` applies UFW rules based on per-model JSON configs. It supports application profiles, single ports, and port ranges with IP whitelisting. The program prints rule previews and waits for user confirmation before applying changes."
    },
    {
      title: "Service Deployment Flow",
      img: "DebianServicesFlow.png",
      alt: "Custom Service Setup Logic",
      text: "`DebianServices.py` installs or removes systemd services and associated scripts. It validates file paths, copies templates, enables autostart, and supports optional logrotate configuration. Admins can also review logs via the built-in viewer."
    },
    {
      title: "Third-Party APT Installer Flowchart",
      img: "DebianThirdPartyFlow.png",
      alt: "Third-Party Install Logic",
      text: "`DebianThirdPartryInstalls.py` adds external repositories, installs packages, and removes them cleanly if uninstalled. The script detects conflicting keyrings and handles GPG key and source list creation automatically."
    },
    {
      title: "DEB Installer Flowchart",
      img: "DebianDebFlow.png",
      alt: "DEB File Install Logic",
      text: "`DebianDebInstalls.py` handles downloading `.deb` files from URLs, installing them, and optionally enabling systemd services based on configuration. Files are cleaned up after installation, and logs are rotated automatically."
    },
    {
      title: "Flatpak Installer Flowchart",
      img: "DebianFlatpakFlow.png",
      alt: "Flatpak Install Logic",
      text: "`DebianFlatPakInstalls.py` ensures Flatpak and Flathub are available, then installs or uninstalls model-specific apps using a clean interface. Remote configuration is also supported per application."
    },
    {
      title: "APT Package Installer Flowchart",
      img: "DebianPackageFlow.png",
      alt: "APT Install Logic",
      text: "`DebianPackageInstalls.py` handles standard APT packages using a simple model-configured list. It verifies package status before performing any action and supports clean summary logging and feedback."
    }
  ]
};
