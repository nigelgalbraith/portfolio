class SearchTool {
  constructor(name) {
    this.name = name;
    this.factors = [];
  }

  // Normalize any value (array/number/null) to a safe string
  _S(v) {
    if (Array.isArray(v)) return String(v[0] ?? '').trim();
    return String(v ?? '').trim();
  }

  // Find factor by normalized name
  findFactor(factorName) {
    const target = this._S(factorName);
    return this.factors.find(entry => this._S(entry.factor) === target);
  }

  // Add a factor if it doesn't exist
  addFactor(newFactor) {
    if (!this.findFactor(newFactor.factor)) {
      this.factors.push(newFactor);
    }
  }

  // Sort factors (string-wise, safely)
  sortFactors(factors) {
    return factors.sort((a, b) =>
      this._S(a.factor).localeCompare(this._S(b.factor))
    );
  }

  // Populate the factor dropdown list
  populateFactorDropdown() {
    const FactorSelect = document.getElementById('FactorSelect');
    FactorSelect.innerHTML = '';

    const sortedFactors = this.sortFactors(this.factors);

    sortedFactors.forEach(factor => {
      const label = this._S(factor.factor);
      const option = document.createElement('option');
      option.value = label;
      option.text = label;
      FactorSelect.appendChild(option);
    });
  }

  // Update the current table based on the list selection
  updateTable() {
    const FactorSelect = document.getElementById('FactorSelect');
    const selectedFactorName = this._S(FactorSelect.value);
    const selectedFactor = this.findFactor(selectedFactorName);
    const searchToolInfo = document.getElementById('searchToolInfo');
    searchToolInfo.innerHTML = '';

    if (selectedFactor) {
      const tableHTML = selectedFactor.toTable();
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = tableHTML;

      tempDiv.querySelectorAll('.collapsible').forEach(function (heading) {
        heading.addEventListener('click', function () {
          const content = this.nextElementSibling;
          content.style.display =
            (content.style.display === 'none' || content.style.display === '')
              ? 'table-row'
              : 'none';
        });
      });

      searchToolInfo.appendChild(tempDiv.firstChild);
    }
  }

  // To string for SearchTool
  toString() {
    return `Search Tool: ${this.name}, Factors: ${this.factors.map(c => c.toString()).join(', ')}`;
  }
}
