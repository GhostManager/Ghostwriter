// Copyright FIRST, Red Hat, and contributors
// SPDX-License-Identifier: BSD-2-Clause

// CVSS v4.0 metrics ordering and valid values
expectedMetricOrder = {
    // Base (11 metrics)
    "AV": ["N", "A", "L", "P"],
    "AC": ["L", "H"],
    "AT": ["N", "P"],
    "PR": ["N", "L", "H"],
    "UI": ["N", "P", "A"],
    "VC": ["H", "L", "N"],
    "VI": ["H", "L", "N"],
    "VA": ["H", "L", "N"],
    "SC": ["H", "L", "N"],
    "SI": ["H", "L", "N"],
    "SA": ["H", "L", "N"],
    // Threat (1 metric)
    "E": ["X", "A", "P", "U"],
    // Environmental (14 metrics)
    "CR":  ["X", "H", "M", "L"],
    "IR":  ["X", "H", "M", "L"],
    "AR":  ["X", "H", "M", "L"],
    "MAV": ["X", "N", "A", "L", "P"],
    "MAC": ["X", "L", "H"],
    "MAT": ["X", "N", "P"],
    "MPR": ["X", "N", "L", "H"],
    "MUI": ["X", "N", "P", "A"],
    "MVC": ["X", "H", "L", "N"],
    "MVI": ["X", "H", "L", "N"],
    "MVA": ["X", "H", "L", "N"],
    "MSC": ["X", "H", "L", "N"],
    "MSI": ["X", "S", "H", "L", "N"],
    "MSA": ["X", "S", "H", "L", "N"],
    // Supplemental (6 metrics)
    "S":  ["X", "N", "P"],
    "AU": ["X", "N", "Y"],
    "R":  ["X", "A", "U", "I"],
    "V":  ["X", "D", "C"],
    "RE": ["X", "L", "M", "H"],
    "U":  ["X", "Clear", "Green", "Amber", "Red"],
}
