// js/JSON/projectSteps.js

const ProjectSteps = {
// Step-by-step breakdown for the Thematic Analysis project
thematic: [
    {
    title: "Thematic Analysis Structure and Relationships",
    img: "ThematicAnalysisStructureEDR.png",
    alt: "Thematic Analysis Structure and Relationships",
    text: "This project uses a structured workflow to transform raw text into meaningful insights. The thematic analysis links Extracts (raw data) to Factors (identified themes), which are then grouped into Groups, Sub-Groups, and categorized further if needed. This structured hierarchy allows for visualizations, risk models, and filtering in the final web output.Starting in Excel users record and classify data. A Python script converts the workbook into structured JSON allowing the data to be viewed visually in the webpages"
  },
  {
    title: "Thematic Analysis Diagram",
    img: "ThematicAnalysisDataFlow.png",
    alt: "Diagram showing hierarchical flow of thematic analysis",
    text: "This diagram illustrates how the thematic analysis connects each stage of the process. Starting from the central Thematic Analysis, the flow branches into Factor Analysis, which is split into Glossary and Search Tool components. Each of these then links to their associated entities, such as factors, groups, sub-groups, categories, and sub-categories. The visualization highlights the structured relationships that guide how data moves from initial extraction to organized insights."
  },
  {
    title: "Step 1: Enter Extracts and Identify Factors",
    img: "ThematicAnalysisIntial.png",
    alt: "Entering Extracts and Factors",
    text: "Begin by collecting qualitative data such as participant quotes, observations, or written feedback. Each relating data point, referred to as an 'extract,' is entered into the Excel workbook. Alongside each extract, note any recurring themes, patterns, or ideas, which are captured 'factors.' If you are entering a factor manually, first set the mode to 'Manual' to avoid duplication caused by the macro. Once factors are added to the glossary table, they become available for selection via the drop-down list at that point, switch the mode back to 'List' to enable the selection to help maintain consistency. If you need to edit or delete specific factors later, switch to 'Manual' mode before making changes to prevent any macro interference."
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
    text: "Return to the Thematic Analysis sheet and click the 'Update Group' and 'Update Sub Group' buttons. These will populate the appropriate values from your Glossary Table. If you also need to edit factor entries manually such as updating or deleting values be sure to switch the mode to 'Manual' first to prevent duplication or conflicts caused by the macro. Once editing is complete, switch back to 'List' mode to resume structured selection. The sheet highlights missing factors from the glossary in red, providing feedback if anything is incomplete."
  },
  {
    title: "Step 5. Refresh the Search Tool Dataset",
    img: "UpdateSearchTool.png",
    alt: "Search Tool Data",
    text: "This step pulls everything together. Run the update function to copy all the finalized factors and their assignments into the Search Tool Data sheet. This dataset is used in the dropdown filters and logic behind the web-based search tool."
  },
  {
    title: "Step 6. Define Categories and Sub-Categories",
    img: "UpdateCatSubCat.png",
    alt: "Finalizing Categories",
    text: "Add or review the Category and Sub-Category tags for each factor. You can use the buttons to automatically fill these in from the Glossary Table. Add new rows if you've introduced additional themes during your review."
  },
  {
    title: "Step 7. Export for Web Use",
    img: "TAWebUpdateFlow.png",
    alt: "Exporting Thematic Analysis",
    text: "Once everything looks good, save the workbook as 'Thematic-Analysis-Complete.xlsm'. Then un the Python-Update-Webpage.py script (the one that now owns all constants). If you need to change paths or sheet settings, update the IMPORT_CFG and CLEAN_CFG blocks inside Python-Update-Webpage.py. This script turns your structured Excel data into JSON and HTML, which power the web pages for analysis and search."
  },
  {
    title: "Site HTML Structure Overview",
    img: "ThematicAnalysisHTMLStructure.png",
    alt: "Thematic Analysis HTML Page Structure",
    text: "This diagram illustrates the overall structure of the HTML pages in the thematic analysis tool. Each page serves a specific purpose in presenting analysis results, grouped content, and detailed views."
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
    text: "Once data is exported to JSON, a set of JavaScript modules process and display it within each page. This diagram shows the relationships between the various scripts (`intGroupAnalysis.js`, `RiskMatrix.js`, etc.) and their associated data files. It helps make sense of how your thematic structure is rendered across the site."
  },
  {
    title: "Search Tool JavaScript and Data Flow",
    img: "SearchToolHTMLStructure.png",
    alt: "Search Tool Site Map",
    text: "This diagram illustrates the simplified structure of the Search Tool interface. It shows how the main HTML page (`Index.html`) connects to key JavaScript controllers (`initSearchTool.js`, `SearchTool.js`) and the  dataset (`toolJSON.js`). This clear separation makes it easier to understand the flow from page initialization to data filtering logic."
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
    text: "This page lays out your entire thematic structure visually. You’ll see Groups, their linked Factors, and the Extracts they were drawn from. Depending on the data, you might also see visual metrics like risk levels or frequency scores."
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
    text: "Veiw each factor to see how often it appears, what context it's used in, and which themes it supports. This helps surface which ideas are most influential, underused, or worth following up on."
  },
  {
    title: "Group-Level Analysis",
    img: "GroupAnalysisWeb.png",
    alt: "Thematic Analysis Group Analysis Output",
    text: "This breakdown shows the size, spread, and relative weight of each Group. You can compare how often each theme is mentioned and how it connects to others. It’s helpful when you want to identify dominant topics or check for gaps in analysis coverage."
  },
  {
    title: "Sub-Group Analysis",
    img: "SubGroupAnalysisWeb.png",
    alt: "Thematic Analysis Sub Group Analysis Output",
    text: "Shows more focused themes within each Group. Sub-Groups can highlight niche concerns, outliers, or specific issues tied to a broader topic. Use this when you need to fine-tune your insights."
  },
  {
    title: "Risk Model Creator",
    img: "RiskModelCreatorWeb.png",
    alt: "Thematic Analysis Risk Model Creator Output",
    text: "This tool lets you build custom risk models based on the grouped factors. You can define scenarios, assign risk levels, and visually map out how different themes impact potential outcomes. It's useful if you’re turning qualitative data into action plans or dashboards."
  }
  ],

  // Step-by-step breakdown for the quiz creator project
  quiz: [
  {
    title: "Quiz Creator System Overview",
    img: "QuizCreatorStructure.png",
    alt: "Quiz Creator Site Map",
    text: "This diagram shows the structure of the quiz system. The HTML pages load the core JavaScript modules, which in turn access a shared JSON file for all quiz data. This separation of structure, logic, and content allows for flexible updates and easy maintenance."
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
    text: "Once your spreadsheet is finalised, run Python-Update-Webpage.py. It converts Excel → JSON and then cleans/exports the JS using the constants defined in that file. This script updates the quiz content by extracting data from the Excel workbook, formatting it, and saving new HTML and JSON files used by the quiz interface."
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
    text: "Once the raw JSON is created, this stage cleans and restructures the data. It splits fields like 'Multiple Answers', groups them by module, and wraps the result in a JavaScript variable. This output is injected into the quiz interface."
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
    text: "While the default quizzes use CyberOps examples, you can easily adapt the tool for other topics. Just create a new Excel file using the same structure, then update the Excel path in Python-Update-Webpage.py → IMPORT_CFG['excel_file']. (If needed, also adjust sheet_names, start_row, and output filenames in the same IMPORT_CFG; and the cleaner’s output names in CLEAN_CFG.. The rest of the system will adapt automatically."
  }
  ],
  // Step-by-step breakdown for the Website project
  portfolio: [
    {
    title: "HTML Architecture Plan",
    text: "I began by mapping out the HTML structure of the site deciding on core pages (like About, Resume, Projects), and how they would be linked together. This gave me a clear navigation flow and helped identify which project pages would sit underneath the main Projects page. Planning this first made it easier to keep internal linking and layout consistent.",
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
    text: "The Projects page has its own set of modular JavaScript files, such as `projectListLoader.js`, `carousel.js`, and `embedSketchfab.js`. Each of these loads specific data (like project steps or Sketchfab models). This structure makes it easier updates as more features are added.",
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
      text: "This script loads structured steps from `projectSteps.js` and renders them as sections. It’s good for projects with logical project steps, keeping each step clearly separated and easy to follow.",
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
      text: "This script builds a responsive image carousel from data in `carouselData.js`. It generates slide elements, sets up left/right navigation, and handles auto-advance. Helps for previewing multiple screenshots one space.",
      img: "carouselFlow.png",
      alt: "Flowchart showing how carousel images are loaded and rotated"
    },
    {
      title: "modalZoom.js",
      text: "When users click on a media item (image or model), this script opens a modal for an enlarged view. It allows users to explore the images closer if needed without leaving the page.",
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
      text: "This script reads icon entries from `iconRegistry.js` and generates the clickable icons in the site footer (e.g., GitHub, LinkedIn). It helps with consistent styling and makes it easy to update links globally.",
      img: "footerIconLoaderFlow.png",
      alt: "Flowchart showing how footer icons are built and inserted"
    },
    {
      title: "responsiveImageLoader.js",
      text: "To improve performance, this script checks screen width and selects the best image resolution for the device. It helps avoid loading large images on mobile.",
      img: "responsiveImageLoaderFlow.png",
      alt: "Flowchart showing image resolution selection and loading"
    },
    {
      title: "resumeLoader.js",
      text: "This script builds the timeline on the Resume page using data from `resumeData.js`. It loops through jobs, roles, and dates, and formats them into vertical entries.",
      img: "resumeLoaderFlow.png",
      alt: "Flowchart showing how resume entries are rendered"
    },
    {
      title: "skillsLoader.js",
      text: "Loads the skill set from `skillsData.js`, and creates icons, labels, or badges for each one. Skills are sorted into categories and displayed responsively.",
      img: "skillsLoaderFlow.png",
      alt: "Flowchart showing how skills data is visualized"
    },
    {
      title: "Generate-SiteDiagrams.py",
      text: "This Python script generates Mermaid diagrams for HTML and JavaScript structure. It loads site layout from JSON, writes `.mmd` syntax, and uses the Mermaid CLI to export `.svg` and `.png` diagrams used in the webpages.",
      img: "GenerateSiteDiagramsFlow.png",
      alt: "Flowchart showing how the Mermaid site diagrams are generated"
    },
    {
      title: "Image-Optimizer.py",
      text: "This tool resizes images into multiple screen-specific sizes (desktop, laptop, mobile) and compresses thumbnails and icons. It helps the site stay fast while maintaining image quality.",
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
      text: "If you select Zip Backup, the tool will compress your source files into a timestamped archive. You can choose how often to create a zip (Daily, Weekly, Monthly) and how many previous zip files to retain. This is useful for versioned backups or archival snapshots. ⚠️ Important: Mirror mode can permanently delete files from the destination if they no longer exist in the source. While most cloud providers offer a recycle bin (often ~30 days), recovery is not guaranteed use this mode carefully. Always double-check your source and destination paths before running a backup, especially when using Mirror mode. If you're unsure, it's safer to start with Append mode or Zip Backup to avoid accidental data loss."
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
      text: "This module builds the tree-view picker for selecting multiple source folders. It also manages how those paths are passed back to the main form."
    },
    {
      title: "Step 6: Review the Log",
      img: "BackupLogOutput.png",
      alt: "Backup Log Output",
      text: "After the backup completes, review the on-screen log for results, errors, or skipped files. This feedback confirms that all selected files were processed correctly. A copy of each log is also saved to your home directory under the 'logs' folder, so you can refer back to previous backups even after restarting the program."
    },
  ],
  // Step-by-step breakdown for the Debian Install (minimal version)
  debianInstallSuite: [
    {
      title: "Debian Setup Suite Structure",
      img: "DebianSuiteStructure.png",
      alt: "Debian Configuration Flow Diagram",
      text: `
        <ul>
          <li>Driven by a single loader and a shared <code>AppConfig</code>.</li>
          <li>The loader detects your model, resolves config paths, and validates required keys.</li>
          <li>Actions run through a state machine (plan → confirm → execute).</li>
          <li>All utilities (<code>Packages</code>, <code>DEB</code>, <code>Flatpak</code>, <code>ThirdParty</code>, <code>Firewall</code>, <code>Services</code>, <code>Archive</code>, etc.) follow the same modular pattern.</li>
        </ul>
      `
    },

    // Main state machine
    {
      title: "Main State Machine",
      img: "DebianStateMachineFlow.png",
      alt: "Debian Loader State Machine",
      text: `
        <ul>
          <li>Shows a menu of utilities (Packages, DEB, Flatpak, ThirdParty, Firewall, Services, Archive, etc.).</li>
          <li><b>You select which constants module</b> to run.</li>
          <li>Loader <b>loads that constants module</b> (actions, validation, pipeline states).</li>
          <li>Detects the current model and resolves JSON paths from <code>AppConfig</code>.</li>
          <li>Validates config using the selected module’s rules (incl. secondary checks if defined).</li>
          <li>Builds the status & plan, prompts for confirmation, then runs the pipeline (status / plan / execute).</li>
          <li>Writes logs to the utility’s log directory and rotates per policy.</li>
        </ul>
      `
    },
    // One general constants section
    {
      title: "Constants Overview",
      img: "DebianConstantsFlow.png",
      alt: "Constants and Pipelines Overview",
      text:`<br>
            Each install area uses a constants module that defines how jobs are validated and executed.
            The loader imports one set at a time based on what you’re running. <br>
            <b>Common fields include:</b>

            <ul>
              <li><b>PRIMARY_CONFIG</b> – path to <code>Config/AppConfigSettings.json</code>.</li>
              <li><b>JOBS_KEY</b> – the JSON section name used for jobs (e.g., <code>Packages</code>, <code>DEB</code>, <code>Flatpak</code>, <code>ThirdParty</code>, <code>Firewall</code>, <code>Services</code>, <code>Archive</code>).</li>
              <li><b>VALIDATION_CONFIG</b> – required fields for each job and an example structure; enforced before running.</li>
              <li><b>SECONDARY_VALIDATION</b> – optional nested validation (e.g., port lists, sub-objects).</li>
              <li><b>STATUS_FN_CONFIG</b> – function + fields to determine if a job is installed/present vs absent.</li>
              <li><b>ACTIONS / SUB_MENU</b> – menu entries and which pipeline to invoke (e.g., INSTALL/UNINSTALL/STATUS).</li>
              <li><b>PIPELINE_STATES</b> – ordered steps (functions + args + result keys) for each action.</li>
              <li><b>LOG_* (LOG_DIR, LOG_PREFIX, ROTATE_LOG_NAME, LOGS_TO_KEEP)</b> – log paths and rotation policy.</li>
              <li><b>REQUIRED_USER</b> – optional user context guard for safe execution.</li>
            </ul>

            <b>Example (Archive): jobs can define fields like:</b>
            <ul>
              <li><code>DownloadURL</code></li>
              <li><code>ExtractTo</code></li>
              <li><code>StripTopLevel</code></li>
              <li><code>CheckPath</code></li>
              <li><code>PostInstall</code></li>
              <li><code>PostUninstall</code></li>
              <li><code>TrashPaths</code></li>
              <li><code>DownloadPath</code></li>
            </ul>

            The same validation → plan → pipeline pattern applies.
          `
    },

    // Model linking
    {
      title: "Link Your Model in AppConfigSettings.json",
      img: "DebianEditAppConfig.png",
      alt: "Edit AppConfigSettings.json",
      text: `
        <ul>
          <li>Define your model (e.g., <code>ThinkPadX1</code>) in <code>AppConfigSettings.json</code>.</li>
          <li>Map the model to the correct per-utility JSON files (Packages, DEB, Flatpak, ThirdParty, Firewall, Services, Archive, etc.).</li>
          <li>The loader resolves the model at runtime and falls back to <code>Default</code> when a model key or file is missing.</li>
        </ul>
      `
    },
    // General flow
    {
      title: "General Flow",
      img: "DebianGeneralFlow.png",
      alt: "Unified Execution Flow",
      text: `
              <ol>
                <li><b>Detect & Resolve</b>: Loader reads AppConfig, identifies the model, and resolves JSON paths.</li>
                <li><b>Validate</b>: Required keys are checked using the constants module; optional secondary checks run if defined.</li>
                <li><b>Status & Plan</b>: Builds a status table and an execution plan showing what will be installed, removed, or updated.</li>
                <li><b>Confirm</b>: Presents a summary; proceeds only on confirmation (or runs in plan-only/status-only modes).</li>
                <li><b>Execute & Log</b>: Executes the pipeline states in order, writes logs to the utility’s log directory, and rotates them per policy.</li>
              </ol>

              This single flow covers <code>Packages</code>, <code>DEB</code>, <code>Flatpak</code>, <code>ThirdParty</code>,
              <code>Firewall</code>, <code>Services</code>, <code>Archive</code>, and any future utilities you add.
            `
          
      }
   ],
     // Step-by-step breakdown for the Text Creator project
    textCreator: [
      {
        title: "Text Creator System Overview",
        img: "TextCreatorFlow.png",
        alt: "Text Creator site, Docker, and services overview",
        text: "This diagram shows how the Text Creator is wired together. The browser loads static HTML, CSS, and JavaScript from Nginx. When you generate a Text, the frontend sends a request to Ollama for local LLM text generation, and Piper handles optional text-to-speech. Everything runs on your own machine via Docker, so there are no external APIs or cloud services involved."
      },
      {
        title: "Generator Page Layout and Pane Hooks",
        img: "TextCreatorIndexStructure.png",
        alt: "HTML layout for the Text Generator page",
        text: "The Generator page uses a clean HTML layout with data-pane attributes marking each section of the interface. The JavaScript panes—such as the form builder, checklist builder, preview, and Piper controls—locate their matching data-pane elements and build the UI at runtime. This modular structure keeps the HTML simple while allowing each pane script to handle its own logic and events independently."
      },
      {
        title: "Profile Builder Page Layout and Pane Hooks",
        img: "TextCreatorProfileStructure.png",
        alt: "HTML layout for the Profile Builder page",
        text: "The Profile Builder page follows the same modular pattern, using data-pane attributes to mark areas for form editing, checklists, writing styles, and profile metadata. The builder-specific pane scripts attach themselves to these regions and generate the interactive editing tools. This makes it easy to modify or extend the profile structure without touching the underlying HTML."
      },
      {
        title: "Profile Loader and Status Ticker",
        img: "TextCreatorProfileLoader.png",
        alt: "Profile loader and status ticker area",
        text: "At the top of the page, the Profile Loader pane lets you load a JSON profile from disk or fall back to a default. The Status Ticker pane reads short messages from a JSON file and cycles through them, giving light feedback while profiles load or Texts are generated. Both panes share a simple event system so they stay in sync with the rest of the app."
      },
      {
        title: "Step 1: Load or Create a Profile",
        img: "TextCreatorProfileBuilder.png",
        alt: "Profile Builder screen for editing fields and options",
        text: "Start by loading an existing profile or creating a new one in the Profile Builder page. Here you can define form fields, checklist groups, writing styles, and meta settings such as mode and prompt template. All changes are stored in memory until you export them as JSON, so it’s easy to experiment without breaking anything."
      },
      {
        title: "Step 2: Fill in Text Details",
        img: "TextCreatorForm.png",
        alt: "Text generator form fields",
        text: "On the Generator page, the form pane builds its inputs from the active profile. You can enter recipient details, context, role information, and any other fields the profile defines. Checklist panes sit alongside the form, letting you tick skills, strengths, or talking points that should be included in the final Text."
      },
      {
        title: "Step 3: Generate and Review the Text",
        img: "TextCreatorPreview.png",
        alt: "Generated Text preview pane",
        text: "When you click the generate button, the Preview pane collects values from the form and checklists, builds a structured prompt, and sends it to the Ollama endpoint. The response is rendered into the preview area, where you can read through the Text, make small edits, and regenerate if needed."
      },
      {
        title: "Step 4: Listen with Text-to-Speech",
        img: "TextCreatorPiper.png",
        alt: "Text-to-speech controls using Piper",
        text: "If you want to hear how the Text sounds, the Piper pane can read it aloud. It sends the current preview text to the local Piper HTTP service and plays back the audio. This helps catch awkward phrasing or pacing that might be missed when reading silently."
      },
      {
        title: "Step 5: Export and Reuse Profiles",
        img: "TextCreatorExport.png",
        alt: "Export profile to JSON",
        text: "Once you are happy with a profile, use the Export pane to download it as a JSON file. You can keep different profiles for emails, or more general writing. Loading a profile later restores the same form layout, checklist options, and style settings, which keeps the workflow consistent over time."
      }
    ],
    // Step-by-step breakdown for the Language Translator project
    languageTranslator: [
      {
        title: "Language Translator Overview",
        img: "LanguageTranslatorFlow.png",
        alt: "High level flow for the Language Translator",
        text: "This project is a small translation hub that runs entirely in Docker. Nginx serves the static HTML, CSS, and JavaScript, while LibreTranslate provides machine translation and three Piper instances handle text to speech for English, Spanish, and Chinese. The browser talks only to the Nginx routes, which keeps the frontend simple and the services neatly isolated."
      },
      {
        title: "Main Menu and Intro Cards",
        img: "LanguageTranslatorHTMLStructure.png",
        alt: "HTML structure for the Language Translator main page",
        text: "The main Language Translator page presents an intro block and two cards one for Spanish and one for Chinese. Each card is rendered by a reusable intro card pane, which pulls its content from a shared introCard dataset. From here users can jump directly into the translator page for their chosen language."
      },
      {
        title: "Spanish Translator Layout",
        img: "SpanishTranslatorStructure.png",
        alt: "Spanish translator HTML layout",
        text: "The Spanish page is split into two lanes: English → Spanish and Spanish → English. Each lane uses pane scripts for text entry, translation preview, and text to speech playback. A button switch pane wraps each lane so it can be shown or hidden cleanly, but all of the wiring is driven by data attributes in the HTML."
      },
      {
        title: "Chinese Translator Layout",
        img: "ChineseTranslatorStructure.png",
        alt: "Chinese translator HTML layout",
        text: "The Chinese page follows the same pattern as the Spanish page. One lane handles English → Chinese, the other Chinese → English. The same text entry, preview, and Piper panes are reused with different IDs and language codes, showing how the UI modules can be reused just by changing configuration in the markup."
      },
      {
        title: "Translation and TTS Flow",
        img: "LanguageTranslatorFlow.png",
        alt: "Translation and text to speech flow",
        text: "When the user clicks Translate, the preview pane sends the source text and language codes to the /translate route, which Nginx forwards to LibreTranslate. For audio, the Piper panes send the relevant text to one of the TTS routes, which Nginx forwards to the matching Piper container. This keeps network calls consistent and means the UI never needs to know where the services are actually running."
      },
      {
        title: "Translate Text",
        img: "TranslatorTranslate.png",
        alt: "Screenshot showing English to Spanish translation",
        text: "Type your text into the entry box and click Translate. The preview pane updates using the local LibreTranslate service. You can switch direction at any time, making it easy to move between English ↔ Spanish or English ↔ Chinese depending on the page."
      },
      {
        title: "Listen Using Text-to-Speech",
        img: "TranslatorPlayback.png",
        alt: "Screenshot showing playback controls for translated text",
        text: "Once the translation is shown, click the speaker icon to hear it spoken aloud. Each language page uses its own Piper voice engine behind the scenes, routed through Nginx."
      }
    ],
};
