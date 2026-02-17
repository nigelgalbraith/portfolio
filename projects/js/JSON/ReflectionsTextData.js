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
  }
};
