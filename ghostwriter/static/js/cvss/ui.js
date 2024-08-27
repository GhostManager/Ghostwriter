(function() {

  function setCvssBadge(score) {
    const severity = CVSS.severityRating(score);
    document.getElementById("scoreRating").className = "scoreRating " + severity.toLowerCase();
    document.getElementById("baseMetricScore").textContent = score;
    document.getElementById("baseSeverity").textContent = "(" + severity + ")";
  }

  const V3_FIELDS = ["AV", "AC", "PR", "UI", "S", "C", "I", "A"];

  function CVSSV3CalcFromVector(setScore) {
    const cvssSelected = CVSS.parseVector(document.getElementById("id_cvss_vector").value);
    if(!cvssSelected)
      return;

    const score = CVSS.calculateCVSSFromObject(cvssSelected);
    setCvssBadge(score.baseMetricScore);
    if(setScore) {
      // Set score when editing the vector but not when loading
      document.getElementById('id_cvss_score').value = baseMetricScore;
    }

    // Populate buttons
    for (const name of V3_FIELDS) {
      document.querySelector(`input[name="cvssv3_${name}"][value="${cvssSelected[name]}"]`).checked = true;
    }
  }

  function CVSSV3AutoCalc() {
    const cvssSelected = {};
    for(const name of V3_FIELDS) {
      const selected = document.querySelector(`input[name="cvssv3_${name}"]:checked`);
      if (!selected)
        return;
      cvssSelected[name] = selected.value;
    }

    var output = CVSS.calculateCVSSFromObject(cvssSelected);
    if (!output.success) {
      return;
    }

    document.getElementById('id_cvss_score').value = output.baseMetricScore;
    setCvssBadge(output.baseMetricScore);
    document.getElementById('id_cvss_vector').value = output.vectorString;
  }

  $(document).ready(function() {
    CVSSV3CalcFromVector(false);
    document.getElementById("id_cvss_vector").addEventListener("input", () => CVSSV3CalcFromVector(true));

    for(const field of V3_FIELDS) {
      for(const el of document.querySelectorAll(`input[name="cvssv3_${field}"]`)) {
        el.addEventListener("input", () => CVSSV3AutoCalc());
      }
    }
  });
})();
