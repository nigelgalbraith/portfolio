class Controller {
  static setup(jsonData) {
    const theSearchTool = new SearchTool('Research Search Tool');

    // Coerce arrays (or null/undefined) to a safe string
    const firstStr = (v) => {
      if (Array.isArray(v)) return String(v[0] ?? '').trim();
      return String(v ?? '').trim();
    };

    jsonData.forEach(entry => {
      const extract  = firstStr(entry["Extracts"]);
      const wrappers = entry["Wrapper"];

      if (wrappers && Array.isArray(wrappers)) {
        wrappers.forEach(wrapperData => {
          const factorName        = firstStr(wrapperData["Factors"]);
          const groupName         = firstStr(wrapperData["Groups"]);
          const subGroupName      = firstStr(wrapperData["Sub Groups"]);
          const catergoryName     = firstStr(wrapperData["Catergories"]);
          const subCatergoryName  = firstStr(wrapperData["Sub Catergories"]);

          // 1) Factor
          let factor = theSearchTool.findFactor(factorName);
          if (!factor) {
            factor = new Factor(factorName);
            theSearchTool.addFactor(factor);
          }

          // 2) Group
          let group = factor.findGroup(groupName);
          if (!group) {
            group = new Group(groupName);
            factor.addGroup(group);
          }

          // 3) Catergory
          let catergory = group.findCatergory(catergoryName);
          if (!catergory) {
            catergory = new Catergory(catergoryName, subGroupName, subCatergoryName);
            group.addCatergory(catergory);
          }

          // 4) Extract
          const extractInstance = new Extract(extract);
          catergory.addExtract(extractInstance);
        });
      } else {
        console.error("Wrapper array is undefined or not an array:", entry);
      }
    });

    return theSearchTool;
  }
}
