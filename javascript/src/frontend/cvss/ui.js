import "./styles.css";
import CVSS from "./v3_calc";
import { cvssv4FromVector, cvssv4ToVector } from "./v4_vector";
import { cvssv4Score } from "./v4_score";

function setCvssBadge(version, score) {
    if (version === "v4") {
        const severity = CVSS.severityRating(score);
        document.querySelector(
            `#cvss-${version}-calculator .baseRating`
        ).className = "scoreRating baseRating " + severity.toLowerCase();
        document.querySelector(
            `#cvss-${version}-calculator .baseMetricScore`
        ).textContent = score;
        document.querySelector(
            `#cvss-${version}-calculator .baseSeverity`
        ).textContent = "(" + severity + ")";
    }

    if (version === "v3") {
        const base = score.baseMetricScore;
        const severity = CVSS.severityRating(base);
        document.querySelector(
            `#cvss-${version}-calculator .baseRating`
        ).className = "scoreRating baseRating " + severity.toLowerCase();
        document.querySelector(
            `#cvss-${version}-calculator .baseMetricScore`
        ).textContent = base;
        document.querySelector(
            `#cvss-${version}-calculator .baseSeverity`
        ).textContent = "(" + severity + ")";

        const temporalScore = score.temporalMetricScore;
        const temporalSeverity = CVSS.severityRating(temporalScore);
        document.querySelector(
            `#cvss-${version}-calculator .temporalRating`
        ).className =
            "scoreRating temporalRating " + temporalSeverity.toLowerCase();
        document.querySelector(
            `#cvss-${version}-calculator .temporalMetricScore`
        ).textContent = temporalScore;
        document.querySelector(
            `#cvss-${version}-calculator .temporalSeverity`
        ).textContent = "(" + temporalSeverity + ")";

        const envScore = score.environmentalMetricScore;
        const envSeverity = CVSS.severityRating(envScore);
        document.querySelector(
            `#cvss-${version}-calculator .envRating`
        ).className = "scoreRating envRating " + envSeverity.toLowerCase();
        document.querySelector(
            `#cvss-${version}-calculator .envMetricScore`
        ).textContent = envScore;
        document.querySelector(
            `#cvss-${version}-calculator .envSeverity`
        ).textContent = "(" + envSeverity + ")";
    }
}

function setSeveritySelect(score) {
    const severity_select = document.getElementById("id_severity");
    severity_select.selectedIndex = [...severity_select.options].findIndex(
        (option) => option.text === CVSS.severityRating(score)
    );
}

function showCalculatorVersion(version) {
    if (version === "v3") {
        document
            .getElementById("cvss-v3-calculator")
            .style.removeProperty("display");
        document.getElementById("cvss-v4-calculator").style.display = "none";
    } else if (version === "v4") {
        document.getElementById("cvss-v3-calculator").style.display = "none";
        document
            .getElementById("cvss-v4-calculator")
            .style.removeProperty("display");
    } else {
        throw new Error("Invalid version (this is a bug): " + version);
    }
}

const V3_FIELDS = [
    "AV",
    "AC",
    "PR",
    "UI",
    "S",
    "C",
    "I",
    "A",
    "E",
    "RL",
    "RC",
    "CR",
    "IR",
    "AR",
    "MAV",
    "MAC",
    "MPR",
    "MUI",
    "MS",
    "MC",
    "MI",
    "MA",
];
const V4_FIELDS = [
    "AV",
    "AC",
    "AT",
    "PR",
    "UI",
    "VC",
    "VI",
    "VA",
    "SC",
    "SI",
    "SA",
    "S",
    "AU",
    "R",
    "V",
    "RE",
    "U",
    "MAV",
    "MAC",
    "MAT",
    "MPR",
    "MUI",
    "MVC",
    "MVI",
    "MVA",
    "MSC",
    "MSI",
    "MSA",
    "CR",
    "IR",
    "AR",
    "E",
];

function onVectorChanged(setScore) {
    const vectorStr = document.getElementById("id_cvss_vector").value;

    const cvssv3Selected = CVSS.parseVector(vectorStr);
    if (cvssv3Selected) {
        const score = CVSS.calculateCVSSFromObject(cvssv3Selected);

        setCvssBadge("v3", score);
        if (setScore) {
            // Set score when editing the vector but not when loading
            document.getElementById("id_cvss_score").value = score;
        }

        // Populate buttons
        for (const name of V3_FIELDS) {
            const value = cvssv3Selected[name] ?? "X";
            document.querySelector(
                `input[name="cvssv3_${name}"][value="${value}"]`
            ).checked = true;
        }
        showCalculatorVersion("v3");
        return;
    }

    const cvssv4Selected = cvssv4FromVector(vectorStr);
    if (cvssv4Selected) {
        const score = cvssv4Score(cvssv4Selected);
        setCvssBadge("v4", score);
        if (setScore) {
            // Set score when editing the vector but not when loading
            document.getElementById("id_cvss_score").value = score;
        }

        // Populate buttons
        for (const name of V4_FIELDS) {
            const value = cvssv4Selected[name] ?? "X";
            document.querySelector(
                `input[name="cvssv4_${name}"][value="${value}"]`
            ).checked = true;
        }
        showCalculatorVersion("v4");
        return;
    }
}

function onV3ButtonChanged() {
    const cvssSelected = {};
    for (const name of V3_FIELDS) {
        const selected = document.querySelector(
            `input[name="cvssv3_${name}"]:checked`
        );
        if (!selected) return;
        cvssSelected[name] = selected.value;
    }

    var output = CVSS.calculateCVSSFromObject(cvssSelected);
    if (!output.success) {
        return;
    }

    // Use modified environmental score if available
    var score =
        output.environmentalMetricScore !== undefined
            ? output.environmentalMetricScore
            : output.baseMetricScore;
    document.getElementById("id_cvss_score").value = score;
    setCvssBadge("v3", output);
    document.getElementById("id_cvss_vector").value = output.vectorString;
    setSeveritySelect(score);
}

function onV4ButtonChanged() {
    const cvssSelected = {};
    for (const name of V4_FIELDS) {
        const selected = document.querySelector(
            `input[name="cvssv4_${name}"]:checked`
        );
        if (!selected) return;
        cvssSelected[name] = selected.value;
    }

    const score = cvssv4Score(cvssSelected);
    const vector = cvssv4ToVector(cvssSelected);

    document.getElementById("id_cvss_score").value = score;
    setCvssBadge("v4", score);
    document.getElementById("id_cvss_vector").value = vector;
    setSeveritySelect(score);
}

document.addEventListener("DOMContentLoaded", () => {
    onVectorChanged(false);
    document
        .getElementById("id_cvss_vector")
        .addEventListener("input", () => onVectorChanged(true));

    for (const field of V3_FIELDS) {
        for (const el of document.querySelectorAll(
            `input[name="cvssv3_${field}"]`
        )) {
            el.addEventListener("input", () => onV3ButtonChanged());
        }
    }
    for (const field of V4_FIELDS) {
        for (const el of document.querySelectorAll(
            `input[name="cvssv4_${field}"]`
        )) {
            el.addEventListener("input", () => onV4ButtonChanged());
        }
    }

    document
        .querySelector("#cvss-v3-calculator button.cvss-switch")
        .addEventListener("click", (ev) => {
            ev.preventDefault();
            showCalculatorVersion("v4");
        });
    document
        .querySelector("#cvss-v4-calculator button.cvss-switch")
        .addEventListener("click", (ev) => {
            ev.preventDefault();
            showCalculatorVersion("v3");
        });
});
