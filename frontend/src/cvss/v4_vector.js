
// CVSS "selected object" is an object with keys corresponding to the 1-to-3 letter short code of the metric
// and values corresponding to the short value of the metric.

/// Formats a CVSS selected object to a CVSS vector string
export function cvssv4ToVector (cvssSelected) {
    let value = "CVSS:4.0";
    for (const [metric, _] of expectedMetricOrder) {
        const selected = cvssSelected[metric];
        if (selected != "X") {
            value = value.concat("/" + metric + ":" + selected);
        }
    }
    return value;
}

/// Parses a CVSS vector string to a CVSS selected object, or null if invalid
export function cvssv4FromVector (vector) {
    const metrics = vector.split("/")
    if (metrics[0] != "CVSS:4.0") {
        console.warn("No cvss prefix", vector, metrics[0]);
        return null
    }
    metrics.shift();

    const toSelect = {}
    let mi = 0
    for (const [expected, expectedValues] of expectedMetricOrder) {
        const [key, value] = mi < metrics.length ? metrics[mi].split(":") : [null,null];
        if(key === expected) {
            if (!expectedValues.includes(value)) {
                console.warn("Invalid value", vector, expected, value);
                return null
            }
            toSelect[expected] = value;
            mi += 1;
        } else if(expectedValues[0] === "X") {
            toSelect[expected] = "X"
        } else {
            console.warn("Missing or misplaced value", vector, key);
        }
    }
    return toSelect;
}

const expectedMetricOrder = [
    // Base (11 metrics)
    ["AV", ["N", "A", "L", "P"]],
    ["AC", ["L", "H"]],
    ["AT", ["N", "P"]],
    ["PR", ["N", "L", "H"]],
    ["UI", ["N", "P", "A"]],
    ["VC", ["H", "L", "N"]],
    ["VI", ["H", "L", "N"]],
    ["VA", ["H", "L", "N"]],
    ["SC", ["H", "L", "N"]],
    ["SI", ["H", "L", "N"]],
    ["SA", ["H", "L", "N"]],
    // Threat (1 metric)
    ["E", ["X", "A", "P", "U"]],
    // Environmental (14 metrics)
    ["CR", ["X", "H", "M", "L"]],
    ["IR", ["X", "H", "M", "L"]],
    ["AR", ["X", "H", "M", "L"]],
    ["MAV", ["X", "N", "A", "L", "P"]],
    ["MAC", ["X", "L", "H"]],
    ["MAT", ["X", "N", "P"]],
    ["MPR", ["X", "N", "L", "H"]],
    ["MUI", ["X", "N", "P", "A"]],
    ["MVC", ["X", "H", "L", "N"]],
    ["MVI", ["X", "H", "L", "N"]],
    ["MVA", ["X", "H", "L", "N"]],
    ["MSC", ["X", "H", "L", "N"]],
    ["MSI", ["X", "S", "H", "L", "N"]],
    ["MSA", ["X", "S", "H", "L", "N"]],
    // Supplemental (6 metrics)
    ["S", ["X", "N", "P"]],
    ["AU", ["X", "N", "Y"]],
    ["R", ["X", "A", "U", "I"]],
    ["V", ["X", "D", "C"]],
    ["RE", ["X", "L", "M", "H"]],
    ["U", ["X", "Clear", "Green", "Amber", "Red"]],
];
