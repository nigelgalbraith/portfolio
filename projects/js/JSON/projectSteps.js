// js/JSON/projectSteps.js

const ProjectSteps = {
  /* -------------------------
     SOFTWARE TOOLS
  ------------------------- */

  portfolio: [
    // Main Site Architecture
    {
      title: "HTML Architecture Plan",
      text: "I started by mapping out the HTML structure of the site, deciding on the core pages such as About, Resume, and Projects, and how they would link together. This gave me a clear navigation flow and helped define which project pages would sit under the main Projects page. Planning the structure first made it easier to keep the layout and internal linking consistent.",
      img: "SiteHTMLStructure.png",
      alt: "Diagram showing how the main HTML pages and project subpages are connected"
    },
    {
      title: "JavaScript Architecture (Main Pages)",
      text: "To keep the site modular, I mapped out which JavaScript files are loaded by each main HTML page. For example, the Resume page loads `resumeLoader.js` and `skillsLoader.js`, which then pull in the data they need. Keeping each script focused on a single job makes the site easier to maintain and update.",
      img: "SiteJSMainPages.png",
      alt: "Diagram showing JavaScript modules and data linked to the main site pages"
    },
    {
      title: "JavaScript Architecture (Project Pages)",
      text: "The Projects page uses its own set of modular JavaScript files, including `projectListLoader.js`, `carousel.js`, and `embedSketchfab.js`. Each loader handles a specific part of the page, such as project data, media, or embedded models. Keeping these responsibilities separate makes the page easier to maintain as new features are added.",
      img: "SiteJSProjectPages.png",
      alt: "Diagram showing JavaScript loaders and data modules used by the Projects page"
    },
    // Core Page System
    {
      title: "init.js",
      text: "This script coordinates the initialization of project page components. Once the DOM is ready, it triggers the relevant loaders such as the project list, Sketchfab embeds, step renderer, and other modules so that each feature loads in the correct order.",
      img: "initFlow.png",
      alt: "Flowchart showing how init.js initializes project page scripts"
    },
    {
      title: "projectListLoader.js",
      text: "This script builds the list of projects shown on the Projects page. It loads project entries from `projectListData.js` and loops through them to generate the project cards dynamically. Each card includes the image, title, and description for the project, which makes it easy to add or update projects without editing the HTML directly.",
      img: "projectListLoaderFlow.png",
      alt: "Flowchart showing how projectListLoader.js loads project data and builds project cards"
    },
    {
      title: "projectStepsData.js",
      text: "This script renders the step-by-step walkthroughs shown on project pages. It reads the relevant step data from `projectSteps.js`, detects which project page is open using a data attribute on the `<body>` element, and dynamically builds the HTML for each step. Each section includes a title, responsive image placeholder, and descriptive text, allowing the same script to render structured walkthroughs for any project.",
      img: "projectStepsDataFlow.png",
      alt: "Flowchart showing how projectStepsData.js loads and renders project steps dynamically"
    },
    {
      title: "projectLinksLoader.js",
      text: "This script generates the action buttons shown on project pages, such as 'View Code', 'Live Demo', or 'Download'. It reads link definitions from `projectLinks.js`, matches them to elements marked with a `data-project-link` attribute, and dynamically builds the HTML buttons and icons. This keeps external project links centralized in one data file rather than hardcoding them into each page.",
      img: "projectLinksLoaderFlow.png",
      alt: "Flowchart showing how projectLinksLoader.js loads project link data and generates action buttons"
    },
    {
      title: "mainTextLoader.js",
      text: "This script loads the homepage introduction text from `mainTextData.js` and inserts it into the appropriate content container. Keeping the text in a data file makes it easier to update or reuse across pages without modifying the HTML structure.",
      img: "mainTextLoaderFlow.png",
      alt: "Flowchart showing how homepage text content is loaded dynamically"
    },
    {
      title: "footerIconLoader.js",
      text: "This script generates the icons shown in the site footer, such as links to GitHub or LinkedIn. It reads icon definitions from `iconRegistry.js`, builds the icon elements, and inserts them into the footer container.",
      img: "footerIconLoaderFlow.png",
      alt: "Flowchart showing how footer icons are generated and inserted"
    },
    {
      title: "resumeLoader.js",
      text: "This script builds the timeline shown on the Resume page. It reads job history data from `resumeData.js`, loops through the entries, and generates the timeline layout dynamically.",
      img: "resumeLoaderFlow.png",
      alt: "Flowchart showing how resumeLoader.js renders resume entries"
    },
    {
      title: "skillsLoader.js",
      text: "This script loads skill data from `skillsData.js` and displays it on the Resume page. Skills are grouped by category and rendered as icons or labels, allowing the page to update automatically when new skills are added to the data file.",
      img: "skillsLoaderFlow.png",
      alt: "Flowchart showing how skillsLoader.js loads and displays skills"
    },
    // Media & Interactive Features
    {
      title: "carousel.js",
      text: "This script creates image carousels for project pages. It reads image data from `carouselData.js`, generates the slide elements, and attaches navigation controls so users can move between images. The script handles slide switching and ensures only one image is visible at a time.",
      img: "carouselFlow.png",
      alt: "Flowchart showing how carousel.js builds and controls image slides"
    },
    {
      title: "modalZoom.js",
      text: "This script enables image zoom functionality. When a user clicks a project image, the script opens a modal window displaying the larger version of the image. This allows users to examine screenshots or diagrams in more detail without leaving the page.",
      img: "modalZoomFlow.png",
      alt: "Flowchart showing how modalZoom.js opens and closes image modals"
    },
    {
      title: "embedSketchfab.js",
      text: "This script embeds Sketchfab 3D models into project pages. It reads model information from `sketchfabModels.js`, creates the appropriate iframe embed code, and inserts it into elements marked with a `data-sketchfab` attribute. This allows interactive 3D models to be added to project pages without writing the embed code directly in the HTML.",
      img: "embedSketchfabFlow.png",
      alt: "Flowchart showing how Sketchfab models are embedded into project pages"
    },
    {
      title: "githubAppLoader.js",
      text: "This script loads GitHub app metadata from `githubApps.js` and builds links for each app, such as Play, Download, and Source. It inserts these links into containers marked with a `data-github-app` attribute, allowing apps to be added or updated without editing the HTML directly.",
      img: "githubAppLoaderFlow.png",
      alt: "Flowchart showing how githubAppLoader.js reads app data and generates links"
    },
    // Site UI Systems
    {
      title: "menuToggle.js",
      text: "This script manages the mobile navigation menu. When the hamburger icon is clicked, it toggles a CSS class that expands or collapses the menu. This allows the site navigation to work cleanly on smaller screens.",
      img: "menuToggleFlow.png",
      alt: "Flowchart showing how the mobile menu toggle works"
    },
    {
      title: "themeToggle.js",
      text: "This script manages the site's light and dark mode settings. When the user toggles the theme switch, the script updates the page theme and stores the preference so it remains consistent across page loads.",
      img: "themeToggleFlow.png",
      alt: "Flowchart showing how the theme toggle switches between light and dark modes"
    },
    {
      title: "responsiveImageLoader.js",
      text: "This script loads responsive images for project pages. It detects the screen size and selects the most appropriate image resolution from the available versions. This helps improve page performance by avoiding unnecessarily large image downloads on smaller devices.",
      img: "responsiveImageLoaderFlow.png",
      alt: "Flowchart showing how responsiveImageLoader.js selects image sizes"
    },
    // Development Tools
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
    title: "Excel to Quiz JSON Import",
    img: "QuizImportFlow.png",
    alt: "Quiz Excel Import",
    text: "This stage reads the structured Excel file and combines all the module sheets into a single JSON file. Each sheet's questions, answers, and metadata are converted to structured records. This ensures all quiz content is accurately captured before it's cleaned or displayed."
  },
  {
    title: "Quiz Data Cleaning and Script Injection",
    img: "QuizCleanFlow.png",
    alt: "Quiz Cleaning and Injection",
    text: "Once the raw JSON is created, this stage cleans and restructures the data. It splits fields like 'Multiple Answers', groups them by module, and wraps the result in a JavaScript variable. This output becomes the dataset used by the quiz interface."
  },
  {
    title: "Step 2: Run the Quiz Update Script",
    img: "quizWebUpdateFlow.png",
    alt: "Quiz Python Program Flow Chart",
    text: "Once your spreadsheet is finalised, run Python-Update-Webpage.py. The script imports the Excel workbook, converts it to JSON, cleans and groups the quiz data, and exports a JavaScript file used by the quiz application."
  },
  {
    title: "Step 3: Launch the Quiz Selector",
    img: "QuizCreatorScreenShot-QuizIndex.png",
    alt: "Quiz Main Page",
    text: "Open the index.html file to launch the quiz selector page. From here users can choose which module quiz to take. Each quiz loads its questions from the dataset generated by the update script."
  },
  {
    title: "Step 4: Submit and Check Your Answers",
    img: "QuizCreatorScreenShot-QuizPostAns.png",
    alt: "Quiz Question Check",
    text: "As users complete the quiz they can submit answers and receive immediate feedback. The system highlights the correct answer and displays the explanation stored in the dataset."
  },
  {
    title: "Step 5: Review the Quiz Summary",
    img: "QuizCreatorScreenShot-QuizRedsults.png",
    alt: "Quiz Results",
    text: "After completing all questions, submitting the quiz generates a results summary. The summary shows the number of correct answers and highlights any questions that were answered incorrectly."
  },
  {
    title: "Step 6: Build and Load Custom Quizzes",
    img: "QuizCreatorScreenShot-QuizExcelSheetDefine.png",
    alt: "Quiz ExcelSheet Definition",
    text: "You can create new quizzes by building another Excel file using the same column structure. Update the Excel path in Python-Update-Webpage.py (IMPORT_CFG['excel_file']) and run the update script again. The system will rebuild the quiz dataset automatically."
  }
],

thematic: [
  {
  title: "Thematic Analysis Structure and Relationships",
  img: "ThematicAnalysisStructureEDR.png",
  alt: "Thematic Analysis Structure and Relationships",
  text: "This project uses a structured workflow to transform raw text into meaningful insights. The thematic analysis links Extracts (raw data) to Factors (identified themes), which are then grouped into Groups, Sub-Groups, and categorized further if needed. This structured hierarchy supports visualizations, risk models, and filtering in the final web output. Starting in Excel, users record and classify data. A Python script converts the workbook into structured JSON, allowing the data to be viewed visually in the web pages."
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
  text: "Begin by collecting qualitative data such as participant quotes, observations, or written feedback. Each related data point, referred to as an 'extract', is entered into the Excel workbook. Alongside each extract, note any recurring themes, patterns, or ideas, which are captured as 'factors'. If you are entering a factor manually, first set the mode to 'Manual' to avoid duplication caused by the macro. Once factors are added to the glossary table they become available for selection via the drop-down list. At that point switch the mode back to 'List' to maintain consistent selections. If you need to edit or delete specific factors later, switch to 'Manual' mode before making changes to prevent macro interference."
  },
  {
  title: "Step 2: View Identified Factors",
  img: "FactorInput.png",
  alt: "Viewing Factors",
  text: "After populating the initial extract and factor fields, the built-in Excel macro provides a consolidated view of all identified factors. This is a chance to catch spelling inconsistencies, repeated entries, or missing values. Reviewing this list before progressing helps ensure the thematic framework remains consistent and reduces downstream confusion."
  },
  {
  title: "Step 3: Populate the Glossary Table",
  img: "PopulateGlossary.png",
  alt: "Glossary Table",
  text: "The glossary serves as a thematic map. Here each factor is assigned to broader Groups and Sub-Groups. This classification adds structure and makes it easier to interpret patterns at scale. Instead of viewing factors in isolation, the glossary relates them to higher-level themes, improving both clarity and usability in the final web output."
  },
  {
  title: "Step 4: Assign Group and Sub-Group Values",
  img: "UpdateGroupSubGroup.png",
  alt: "Group and Sub-Group Update",
  text: "Return to the Thematic Analysis sheet and click the 'Update Group' and 'Update Sub Group' buttons. These populate the appropriate values from your Glossary Table. If you need to edit factor entries manually, such as updating or deleting values, switch to 'Manual' mode first to prevent duplication or macro conflicts. Once editing is complete, switch back to 'List' mode to resume structured selection. The sheet highlights missing glossary entries in red to indicate incomplete mappings."
  },
  {
  title: "Step 5: Refresh the Search Tool Dataset",
  img: "UpdateSearchTool.png",
  alt: "Search Tool Data",
  text: "This step pulls everything together. Run the update function to copy all finalized factors and their assignments into the Search Tool Data sheet. This dataset powers the dropdown filters and logic behind the web-based search interface."
  },
  {
  title: "Step 6: Define Categories and Sub-Categories",
  img: "UpdateCatSubCat.png",
  alt: "Finalizing Categories",
  text: "Add or review the Category and Sub-Category tags for each factor. You can use the buttons to automatically populate these from the Glossary Table. Add new rows if additional themes were introduced during review."
  },
  {
  title: "Step 7: Export for Web Use",
  img: "TAWebUpdateFlow.png",
  alt: "Exporting Thematic Analysis",
  text: "Once everything looks correct, save the workbook as 'Thematic-Analysis-Complete.xlsm'. Then run the Python-Update-Webpage.py script, which manages all constants. If paths or sheet settings need adjustment, update the IMPORT_CFG and CLEAN_CFG sections inside Python-Update-Webpage.py. This script converts the structured Excel data into JSON and HTML used by the analysis webpages."
  },
  {
  title: "Site HTML Structure Overview",
  img: "ThematicAnalysisHTMLStructure.png",
  alt: "Thematic Analysis HTML Page Structure",
  text: "This diagram illustrates the overall structure of the HTML pages in the thematic analysis tool. Each page serves a specific role in presenting analysis results, grouped content, and detailed thematic views."
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
  text: "This Python script loads raw thematic data from multiple JSON files, removes unwanted characters, restructures nested fields, and groups related records together. The cleaned output is then saved in both raw JSON and JavaScript-ready formats."
  },
  {
  title: "JavaScript and Data Flow Structure",
  img: "ThematicAnalysisJSPages.png",
  alt: "Thematic Analysis JavaScript and JSON Relationships",
  text: "Once the data is exported to JSON, a set of JavaScript modules process and display it across the analysis pages. This diagram shows the relationships between scripts such as intGroupAnalysis.js and RiskMatrix.js and their associated datasets."
  },
  {
  title: "Search Tool JavaScript and Data Flow",
  img: "SearchToolHTMLStructure.png",
  alt: "Search Tool Site Map",
  text: "This diagram illustrates the structure of the Search Tool interface. The main HTML page connects to controllers such as initSearchTool.js and SearchTool.js along with the dataset toolJSON.js. This separation keeps the interface logic clear and maintainable."
  },
  {
  title: "Step 8: Use the Search Tool Webpage",
  img: "WebSearchTool.png",
  alt: "Search Tool Output",
  text: "With the export complete you can explore the data through the interactive Search Tool. Use the dropdown filters to search by Category, Sub-Category, Group, or Sub-Group. The tool also includes a glossary and a full factor list to help trace themes back to their original extracts."
  },
  {
  title: "Step 9: Review the Thematic Analysis Web Output",
  img: "ThematicWebResults.png",
  alt: "Thematic Analysis Output",
  text: "This page displays the complete thematic structure visually. Groups, their linked factors, and the extracts they originated from are shown together, allowing patterns to be explored across the dataset."
  },
  {
  title: "Groupings Overview",
  img: "GroupingsWeb.png",
  alt: "Thematic Analysis Groupings Output",
  text: "This visualization shows how factors cluster into broader themes. It provides a quick way to identify where patterns are forming and which thematic areas are most densely represented."
  },
  {
  title: "Factor-Level Analysis",
  img: "FactorAnalysisWeb.png",
  alt: "Thematic Analysis Factor Analysis Output",
  text: "View each factor to see how often it appears, what context it occurs in, and which themes it supports. This helps identify influential ideas, underrepresented areas, or themes worth further investigation."
  },
  {
  title: "Group-Level Analysis",
  img: "GroupAnalysisWeb.png",
  alt: "Thematic Analysis Group Analysis Output",
  text: "This breakdown shows the size and spread of each Group. It allows comparison of how frequently each theme appears and how it connects to other areas of the analysis."
  },
  {
  title: "Sub-Group Analysis",
  img: "SubGroupAnalysisWeb.png",
  alt: "Thematic Analysis Sub Group Analysis Output",
  text: "Sub-group analysis highlights more focused themes within each Group. These can reveal niche concerns, outliers, or detailed aspects of broader topics."
  },
  {
  title: "Risk Model Creator",
  img: "RiskModelCreatorWeb.png",
  alt: "Thematic Analysis Risk Model Creator Output",
  text: "This tool allows you to build custom risk models from the grouped factors. You can define scenarios, assign risk levels, and visualize how themes influence potential outcomes."
  }
],

dataAnalysisTool: [
  {
    title: "Data Analysis Tool Structure",
    img: "DataAnalysisStructure.png",
    alt: "Data Analysis Tool Structure Diagram",
    text: "This diagram shows the overall structure of the Data Analysis Tool. The system runs as a Docker-based stack with separate web, API, and PostgreSQL services. The API is organised into blueprint routes and service modules, while supporting storage areas handle configuration data, backups, and import utilities."
  },
  {
    title: "Data Analysis Tool Workflow",
    img: "DataAnalysisFlow.png",
    alt: "Data Analysis Tool Workflow Diagram",
    text: "This diagram shows the main workflow of the tool. A user starts by selecting a database, then reviews relationships between tables, configures summary settings, generates a summary table, and uses the data entry tools to add or edit records."
  },
  {
    title: "Step 1: Database Settings",
    img: "DataAnalysisToolDatabaseSettingsPage.png",
    alt: "Database Settings Page",
    text: "The workflow begins on the Database Settings page, where a database can be selected, created, or prepared for use. This gives the rest of the application a database context to work with."
  },
  {
    title: "Step 2: Relationships",
    img: "DataAnalysisToolRelationshipsPage.png",
    alt: "Relationships Page",
    text: "The Relationships page is used to inspect how tables are linked. This helps make the structure of the database easier to understand before building summaries or entering records."
  },
  {
    title: "Step 3: Summary Settings",
    img: "DataAnalysisToolSummarySettingsPage.png",
    alt: "Summary Settings Page",
    text: "The Summary Settings page is used to define how summary data should be generated. This stage controls what information will be grouped, filtered, or displayed in the summary view."
  },
  {
    title: "Step 4: Summary Table",
    img: "DataAnalysisToolSummaryTablePage.png",
    alt: "Summary Table Page",
    text: "The Summary Table page displays the generated results in a more usable overview form. This allows the user to review the processed data before making record-level changes."
  },
  {
    title: "Step 5: Data Entry",
    img: "DataAnalysisToolDataEntryPage.png",
    alt: "Data Entry Page",
    text: "The Data Entry page allows records to be added, edited, or removed while working within the database structure already defined by the selected tables and relationships."
  }
],

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
    {
      title: "Step 7: Schedule Automatic Backups",
      img: "BackupSchedule.png",
      alt: "Scheduling Automatic Backups",
      text: "A scheduling feature allows the tool to create a Windows Scheduled Task directly from the GUI. Select the desired frequency (Daily, Weekly, or Monthly) and the time the backup should run, then click the 'Schedule Backup' button. The tool will create or update a Windows scheduled task so the backup runs automatically without needing to open the application. This makes it easy to protect files regularly without remembering to run the backup manually."
    },
  ],
  /* -------------------------
     AUTOMATION SYSTEMS
  ------------------------- */

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

  automationTools: [
  {
    title: "Automation Tools Structure",
    img: "AutomationToolsStructure.png",
    alt: "Automation Tools configuration flow diagram",
    text: `
      <ul>
        <li>Driven by a single loader and tool specific constants modules.</li>
        <li>The loader selects the tool, resolves config and documentation paths, and validates required fields.</li>
        <li>Actions run through a shared state machine and ordered pipeline states.</li>
        <li>The framework is designed so new automation tools can follow the same modular pattern without rewriting the loader.</li>
      </ul>
    `
  },
  {
    title: "Main State Machine",
    img: "AutomationToolsStateMachineFlow.png",
    alt: "Automation Tools loader state machine",
    text: `
      <ul>
        <li>Shows the available automation tools and actions.</li>
        <li><b>You select which constants module</b> to run.</li>
        <li>Loader <b>loads that constants module</b> including actions, validation rules, and pipeline states.</li>
        <li>Reads the selected tool’s config and documentation paths.</li>
        <li>Validates config before execution begins.</li>
        <li>Builds the plan, prompts for confirmation, then runs the selected pipeline.</li>
      </ul>
    `
  },
  {
    title: "Constants Overview",
    img: "AutomationToolsConstantsFlow.png",
    alt: "Automation Tools constants and pipelines overview",
    text: `
      <br>
      Each automation tool uses a constants module that defines how the loader should validate and execute that tool.
      The loader imports one set at a time based on what you select. <br>
      <b>Common fields include:</b>

      <ul>
        <li><b>PRIMARY_CONFIG</b> – path to the main config file for the selected tool.</li>
        <li><b>DOC_PATH</b> – path to the matching documentation or help JSON.</li>
        <li><b>VALIDATION_CONFIG</b> – required fields and expected structure for the tool config.</li>
        <li><b>SECONDARY_VALIDATION</b> – optional deeper checks for nested values.</li>
        <li><b>ACTIONS / SUB_MENU</b> – menu entries and which pipeline to run.</li>
        <li><b>PIPELINE_STATES</b> – ordered steps for each action.</li>
        <li><b>REQUIRED_USER</b> – optional execution guard when a specific user context is required.</li>
      </ul>

      The same validation → plan → pipeline pattern applies across the framework.
    `
  },
  {
    title: "Link Tool Config and Documentation",
    img: "AutomationToolsConfigLink.png",
    alt: "Automation Tools config and documentation linkage",
    text: `
      <ul>
        <li>Each tool points to its own config file and matching documentation file.</li>
        <li>The loader reads those paths from the selected constants module.</li>
        <li>This keeps the framework modular by separating tool specific settings from shared execution logic.</li>
      </ul>
    `
  },
  {
    title: "General Flow",
    img: "AutomationToolsGeneralFlow.png",
    alt: "Automation Tools unified execution flow",
    text: `
      <ol>
        <li><b>Select Tool</b>: Loader shows the menu and loads the chosen constants module.</li>
        <li><b>Resolve Config</b>: Reads the config and documentation paths for that tool.</li>
        <li><b>Validate</b>: Required keys are checked before anything runs.</li>
        <li><b>Status & Plan</b>: Builds a clear execution plan for the selected action.</li>
        <li><b>Confirm</b>: Presents a summary and proceeds only when confirmed.</li>
        <li><b>Execute</b>: Runs the pipeline states.</li>
      </ol>

      This single flow allows different automation tools to reuse the same loader without duplicating control logic.
    `
  }
],

  testingTools: [
    {
      title: "Testing Tools Structure",
      img: "TestingToolsStructure.png",
      alt: "Testing Tools configuration flow diagram",
      text: `
        <ul>
          <li>Driven by a shared loader and separate constants modules for each scanner.</li>
          <li>The loader selects the scanner, resolves config and documentation paths, and validates required fields.</li>
          <li>Actions run through the same state machine and ordered pipeline pattern used across the framework.</li>
          <li>WiFi and network diagnostics follow the same modular structure, making the tools easier to extend and maintain.</li>
        </ul>
      `
    },
    {
      title: "Main State Machine",
      img: "TestingToolsStateMachineFlow.png",
      alt: "Testing Tools loader state machine",
      text: `
        <ul>
          <li>Shows a menu of available diagnostic tools such as WiFi scanning and network scanning.</li>
          <li><b>You select which constants module</b> to run.</li>
          <li>Loader <b>loads that constants module</b> including actions, validation rules, and pipeline states.</li>
          <li>Reads the selected tool’s config and documentation paths.</li>
          <li>Validates config before running any scan action.</li>
          <li>Builds the plan, prompts for confirmation, then runs the selected pipeline.</li>
        </ul>
      `
    },
    {
      title: "Constants Overview",
      img: "TestingToolsConstantsFlow.png",
      alt: "Testing Tools constants and pipelines overview",
      text: `
        <br>
        Each diagnostic tool uses a constants module that defines how the loader should validate and execute that scanner.
        The loader imports one set at a time based on what you’re running. <br>
        <b>Common fields include:</b>

        <ul>
          <li><b>PRIMARY_CONFIG</b> – path to the selected scanner config file.</li>
          <li><b>DOC_PATH</b> – path to the matching documentation or help JSON.</li>
          <li><b>VALIDATION_CONFIG</b> – required fields and expected structure for the scanner config.</li>
          <li><b>SECONDARY_VALIDATION</b> – optional deeper checks for nested values.</li>
          <li><b>ACTIONS / SUB_MENU</b> – available scan actions and which pipeline to run.</li>
          <li><b>PIPELINE_STATES</b> – ordered steps for each scan action.</li>
          <li><b>REQUIRED_USER</b> – optional execution guard if needed for a scanner action.</li>
        </ul>

        The same validation → plan → pipeline pattern applies across both WiFi and network tools.
      `
    },
    {
      title: "Link Scanner Config and Documentation",
      img: "TestingToolsConfigLink.png",
      alt: "Testing Tools config and documentation linkage",
      text: `
        <ul>
          <li>Each scanner points to its own config file and matching documentation file.</li>
          <li>The loader reads those paths from the selected constants module.</li>
          <li>This keeps WiFi and network specific settings separate from the shared execution logic.</li>
        </ul>
      `
    },
    {
      title: "General Flow",
      img: "TestingToolsGeneralFlow.png",
      alt: "Testing Tools unified execution flow",
      text: `
        <ol>
          <li><b>Select Tool</b>: Loader shows the menu and loads the chosen scanner constants module.</li>
          <li><b>Resolve Config</b>: Reads the config and documentation paths for that scanner.</li>
          <li><b>Validate</b>: Required keys are checked before any diagnostics run.</li>
          <li><b>Status & Plan</b>: Builds a clear execution plan for the selected scan action.</li>
          <li><b>Confirm</b>: Presents a summary and proceeds only when confirmed.</li>
          <li><b>Execute</b>: Runs the pipeline states in order.</li>
        </ol>

        This single flow supports both WiFi scanning and network scanning without duplicating the overall control structure.
      `
    }
  ],
  /* -------------------------
     AI / LLM TOOLS
  ------------------------- */

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

    promptForge: [
    {
      title: "Prompt Forge System Overview",
      img: "PromptForgeFlow.png",
      alt: "Prompt Forge site, API, and local model services overview",
      text: "This diagram shows how Prompt Forge is structured. The browser loads the static frontend through Nginx, while a lightweight Node and Express API handles profile management and prompt generation requests. Local providers such as Ollama or LocalAI handle the actual model processing, keeping the whole workflow self hosted and under your control."
    },
    {
      title: "Frontend Layout and Pane Structure",
      img: "PromptForgeIndexStructure.png",
      alt: "Prompt Forge frontend HTML structure",
      text: "The interface is split into reusable sections for profile loading, prompt building, output preview, and batch generation. Each area is wired through small JavaScript modules rather than a large frontend framework. This keeps the page easier to understand, easier to extend, and more in line with the lightweight style used across the rest of the project."
    },
    {
      title: "API and Profile Management Flow",
      img: "PromptForgeApiFlow.png",
      alt: "Prompt Forge API and profile management flow",
      text: "The API layer handles loading, saving, and updating JSON based prompt profiles. Instead of hardcoding form setups into the page, Prompt Forge reads structured profile data and rebuilds the interface from that configuration. This makes it easier to reuse prompt layouts and keep the workflow consistent across different writing tasks."
    },
    {
      title: "Step 1: Load or Create a Prompt Profile",
      img: "PromptForgeProfileLoader.png",
      alt: "Prompt Forge profile loader",
      text: "Start by loading an existing profile or creating a new one. Profiles define the form fields, prompt template, metadata, and any reusable options you want available in the interface. This means the tool can be adapted for different writing or prompt building tasks without rewriting the frontend."
    },
    {
      title: "Step 2: Fill in Prompt Inputs",
      img: "PromptForgeForm.png",
      alt: "Prompt Forge form inputs",
      text: "Once a profile is active, the page builds the required inputs dynamically. You can enter the context, role, style, instructions, or any custom fields defined by the selected profile. This keeps the workflow structured and avoids rebuilding the same prompt format manually each time."
    },
    {
      title: "Step 3: Choose Provider and Generate Output",
      img: "PromptForgePreview.png",
      alt: "Prompt Forge generated output preview",
      text: "After filling in the prompt details, the request is sent through the API to the selected local provider. The generated result is then shown in the preview area, where it can be reviewed, copied, or regenerated. Keeping this step local means the prompts and outputs stay on your own machine rather than being sent to an external service."
    },
    {
      title: "Step 4: Run Batch Prompt Jobs",
      img: "PromptForgeBatch.png",
      alt: "Prompt Forge batch generation screen",
      text: "For repeated work, Prompt Forge also supports batch style prompt generation. This lets you apply the same structure to multiple jobs without re entering the full setup every time. It makes the tool more useful for repeatable content workflows instead of just one off prompt testing."
    }
  ],
};
