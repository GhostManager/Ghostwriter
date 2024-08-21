(function () {
    window.CVSSV4AutoCalc = function () {
        const cvssSelected = {};
        for (const [name, _] of window.cvssv4_expectedMetricOrder) {
            const selected = document.querySelector(`input[name="cvssv4_${name}"]:checked`);
            if (!selected)
                return;
            cvssSelected[name] = selected.value;
        }

        const score = window.cvssv4Score(cvssSelected);
        const vector = window.cvssv4ToVector(cvssSelected);
        document.getElementById("id_cvss_v4_score").value = score;
        document.getElementById("id_cvss_v4_vector").value = vector;
    };

    window.CVSSV4CalcFromVector = function () {
        const vector = document.getElementById("id_cvss_v4_vector").value;
        const cvssSelected = window.cvssv4FromVector(vector);
        if (!cvssSelected) {
            return;
        }
        const score = window.cvssv4Score(cvssSelected);
        document.getElementById("id_cvss_v4_score").value = score;

        // populate buttons
        for (const [name, _] of window.cvssv4_expectedMetricOrder) {
            document.querySelector(`input[name="cvssv4_${name}"][value="${cvssSelected[name]}"]`).checked = true;
        }
    }

    $(document).ready(function () {
        window.CVSSV4CalcFromVector();
        document.getElementById("id_cvss_v4_vector").addEventListener("change", window.CVSSV4CalcFromVector);
    });
})();
