// Modified from https://github.com/RedHatProductSecurity/cvss-v4-calculator/tree/main

// The following defines the index of each metric's values.
// It is used when looking for the highest vector part of the
// combinations produced by the MacroVector respective highest vectors.
const AV_levels = { N: 0.0, A: 0.1, L: 0.2, P: 0.3 };
const PR_levels = { N: 0.0, L: 0.1, H: 0.2 };
const UI_levels = { N: 0.0, P: 0.1, A: 0.2 };

const AC_levels = { L: 0.0, H: 0.1 };
const AT_levels = { N: 0.0, P: 0.1 };

const VC_levels = { H: 0.0, L: 0.1, N: 0.2 };
const VI_levels = { H: 0.0, L: 0.1, N: 0.2 };
const VA_levels = { H: 0.0, L: 0.1, N: 0.2 };

const SC_levels = { H: 0.1, L: 0.2, N: 0.3 };
const SI_levels = { S: 0.0, H: 0.1, L: 0.2, N: 0.3 };
const SA_levels = { S: 0.0, H: 0.1, L: 0.2, N: 0.3 };

const CR_levels = { H: 0.0, M: 0.1, L: 0.2 };
const IR_levels = { H: 0.0, M: 0.1, L: 0.2 };
const AR_levels = { H: 0.0, M: 0.1, L: 0.2 };

export function cvssv4Score(cvssSelected) {
    const macroVectorResult = macroVector(cvssSelected);

    // Exception for no impact on system (shortcut)
    if (
        ["VC", "VI", "VA", "SC", "SI", "SA"].every(
            (metric) => m(cvssSelected, metric) == "N"
        )
    ) {
        return 0.0;
    }

    let value = cvssLookup_global[macroVectorResult];

    // 1. For each of the EQs:
    //   a. The maximal scoring difference is determined as the difference
    //      between the current MacroVector and the lower MacroVector.
    //     i. If there is no lower MacroVector the available distance is
    //        set to NaN and then ignored in the further calculations.
    const eq1 = parseInt(macroVectorResult[0]);
    const eq2 = parseInt(macroVectorResult[1]);
    const eq3 = parseInt(macroVectorResult[2]);
    const eq4 = parseInt(macroVectorResult[3]);
    const eq5 = parseInt(macroVectorResult[4]);
    const eq6 = parseInt(macroVectorResult[5]);

    // compute next lower macro, it can also not exist
    const eq1_next_lower_macro = "".concat(eq1 + 1, eq2, eq3, eq4, eq5, eq6);
    const eq2_next_lower_macro = "".concat(eq1, eq2 + 1, eq3, eq4, eq5, eq6);

    // eq3 and eq6 are related
    let eq3eq6_next_lower_macro;
    let eq3eq6_next_lower_macro_left;
    let eq3eq6_next_lower_macro_right;
    if (eq3 == 1 && eq6 == 1) {
        // 11 --> 21
        eq3eq6_next_lower_macro = "".concat(eq1, eq2, eq3 + 1, eq4, eq5, eq6);
    } else if (eq3 == 0 && eq6 == 1) {
        // 01 --> 11
        eq3eq6_next_lower_macro = "".concat(eq1, eq2, eq3 + 1, eq4, eq5, eq6);
    } else if (eq3 == 1 && eq6 == 0) {
        // 10 --> 11
        eq3eq6_next_lower_macro = "".concat(eq1, eq2, eq3, eq4, eq5, eq6 + 1);
    } else if (eq3 == 0 && eq6 == 0) {
        // 00 --> 01
        // 00 --> 10
        eq3eq6_next_lower_macro_left = "".concat(
            eq1,
            eq2,
            eq3,
            eq4,
            eq5,
            eq6 + 1
        );
        eq3eq6_next_lower_macro_right = "".concat(
            eq1,
            eq2,
            eq3 + 1,
            eq4,
            eq5,
            eq6
        );
    } else {
        // 21 --> 32 (do not exist)
        eq3eq6_next_lower_macro = "".concat(
            eq1,
            eq2,
            eq3 + 1,
            eq4,
            eq5,
            eq6 + 1
        );
    }

    const eq4_next_lower_macro = "".concat(eq1, eq2, eq3, eq4 + 1, eq5, eq6);
    const eq5_next_lower_macro = "".concat(eq1, eq2, eq3, eq4, eq5 + 1, eq6);

    // get their score, if the next lower macro score do not exist the result is NaN
    const score_eq1_next_lower_macro = cvssLookup_global[eq1_next_lower_macro];
    const score_eq2_next_lower_macro = cvssLookup_global[eq2_next_lower_macro];

    let score_eq3eq6_next_lower_macro;
    if (eq3 == 0 && eq6 == 0) {
        // multiple path take the one with higher score
        const score_eq3eq6_next_lower_macro_left =
            cvssLookup_global[eq3eq6_next_lower_macro_left];
        const score_eq3eq6_next_lower_macro_right =
            cvssLookup_global[eq3eq6_next_lower_macro_right];

        if (
            score_eq3eq6_next_lower_macro_left >
            score_eq3eq6_next_lower_macro_right
        ) {
            score_eq3eq6_next_lower_macro = score_eq3eq6_next_lower_macro_left;
        } else {
            score_eq3eq6_next_lower_macro = score_eq3eq6_next_lower_macro_right;
        }
    } else {
        score_eq3eq6_next_lower_macro =
            cvssLookup_global[eq3eq6_next_lower_macro];
    }

    const score_eq4_next_lower_macro = cvssLookup_global[eq4_next_lower_macro];
    const score_eq5_next_lower_macro = cvssLookup_global[eq5_next_lower_macro];

    //   b. The severity distance of the to-be scored vector from a
    //      highest severity vector in the same MacroVector is determined.
    const eq1_maxes = getEQMaxes(macroVectorResult, 1);
    const eq2_maxes = getEQMaxes(macroVectorResult, 2);
    const eq3_eq6_maxes = getEQMaxes(macroVectorResult, 3)[
        macroVectorResult[5]
    ];
    const eq4_maxes = getEQMaxes(macroVectorResult, 4);
    const eq5_maxes = getEQMaxes(macroVectorResult, 5);

    // compose them
    const max_vectors = [];
    for (const eq1_max of eq1_maxes) {
        for (const eq2_max of eq2_maxes) {
            for (const eq3_eq6_max of eq3_eq6_maxes) {
                for (const eq4_max of eq4_maxes) {
                    for (const eq5max of eq5_maxes) {
                        max_vectors.push(
                            eq1_max + eq2_max + eq3_eq6_max + eq4_max + eq5max
                        );
                    }
                }
            }
        }
    }

    // Find the max vector to use i.e. one in the combination of all the highests
    // that is greater or equal (severity distance) than the to-be scored vector.
    let severity_distance_AV,
        severity_distance_PR,
        severity_distance_UI,
        severity_distance_AC,
        severity_distance_AT,
        severity_distance_VC,
        severity_distance_VI,
        severity_distance_VA,
        severity_distance_SC,
        severity_distance_SI,
        severity_distance_SA,
        severity_distance_CR,
        severity_distance_IR,
        severity_distance_AR;
    for (let i = 0; i < max_vectors.length; i++) {
        const max_vector = max_vectors[i];
        severity_distance_AV =
            AV_levels[m(cvssSelected, "AV")] -
            AV_levels[extractValueMetric("AV", max_vector)];
        severity_distance_PR =
            PR_levels[m(cvssSelected, "PR")] -
            PR_levels[extractValueMetric("PR", max_vector)];
        severity_distance_UI =
            UI_levels[m(cvssSelected, "UI")] -
            UI_levels[extractValueMetric("UI", max_vector)];

        severity_distance_AC =
            AC_levels[m(cvssSelected, "AC")] -
            AC_levels[extractValueMetric("AC", max_vector)];
        severity_distance_AT =
            AT_levels[m(cvssSelected, "AT")] -
            AT_levels[extractValueMetric("AT", max_vector)];

        severity_distance_VC =
            VC_levels[m(cvssSelected, "VC")] -
            VC_levels[extractValueMetric("VC", max_vector)];
        severity_distance_VI =
            VI_levels[m(cvssSelected, "VI")] -
            VI_levels[extractValueMetric("VI", max_vector)];
        severity_distance_VA =
            VA_levels[m(cvssSelected, "VA")] -
            VA_levels[extractValueMetric("VA", max_vector)];

        severity_distance_SC =
            SC_levels[m(cvssSelected, "SC")] -
            SC_levels[extractValueMetric("SC", max_vector)];
        severity_distance_SI =
            SI_levels[m(cvssSelected, "SI")] -
            SI_levels[extractValueMetric("SI", max_vector)];
        severity_distance_SA =
            SA_levels[m(cvssSelected, "SA")] -
            SA_levels[extractValueMetric("SA", max_vector)];

        severity_distance_CR =
            CR_levels[m(cvssSelected, "CR")] -
            CR_levels[extractValueMetric("CR", max_vector)];
        severity_distance_IR =
            IR_levels[m(cvssSelected, "IR")] -
            IR_levels[extractValueMetric("IR", max_vector)];
        severity_distance_AR =
            AR_levels[m(cvssSelected, "AR")] -
            AR_levels[extractValueMetric("AR", max_vector)];

        // if any is less than zero this is not the right max
        if (
            [
                severity_distance_AV,
                severity_distance_PR,
                severity_distance_UI,
                severity_distance_AC,
                severity_distance_AT,
                severity_distance_VC,
                severity_distance_VI,
                severity_distance_VA,
                severity_distance_SC,
                severity_distance_SI,
                severity_distance_SA,
                severity_distance_CR,
                severity_distance_IR,
                severity_distance_AR,
            ].some((met) => met < 0)
        ) {
            continue;
        }
        // if multiple maxes exist to reach it it is enough the first one
        break;
    }

    const current_severity_distance_eq1 =
        severity_distance_AV + severity_distance_PR + severity_distance_UI;
    const current_severity_distance_eq2 =
        severity_distance_AC + severity_distance_AT;
    const current_severity_distance_eq3eq6 =
        severity_distance_VC +
        severity_distance_VI +
        severity_distance_VA +
        severity_distance_CR +
        severity_distance_IR +
        severity_distance_AR;
    const current_severity_distance_eq4 =
        severity_distance_SC + severity_distance_SI + severity_distance_SA;

    const step = 0.1;

    // if the next lower macro score do not exist the result is Nan
    // Rename to maximal scoring difference (aka MSD)
    const available_distance_eq1 = value - score_eq1_next_lower_macro;
    const available_distance_eq2 = value - score_eq2_next_lower_macro;
    const available_distance_eq3eq6 = value - score_eq3eq6_next_lower_macro;
    const available_distance_eq4 = value - score_eq4_next_lower_macro;
    const available_distance_eq5 = value - score_eq5_next_lower_macro;

    let percent_to_next_eq1_severity = 0;
    let percent_to_next_eq2_severity = 0;
    let percent_to_next_eq3eq6_severity = 0;
    let percent_to_next_eq4_severity = 0;
    let percent_to_next_eq5_severity = 0;

    // some of them do not exist, we will find them by retrieving the score. If score null then do not exist
    let n_existing_lower = 0;

    let normalized_severity_eq1 = 0;
    let normalized_severity_eq2 = 0;
    let normalized_severity_eq3eq6 = 0;
    let normalized_severity_eq4 = 0;
    let normalized_severity_eq5 = 0;

    // multiply by step because distance is pure
    const maxSeverity_eq1 = maxSeverity["eq1"][eq1] * step;
    const maxSeverity_eq2 = maxSeverity["eq2"][eq2] * step;
    const maxSeverity_eq3eq6 = maxSeverity["eq3eq6"][eq3][eq6] * step;
    const maxSeverity_eq4 = maxSeverity["eq4"][eq4] * step;

    //   c. The proportion of the distance is determined by dividing
    //      the severity distance of the to-be-scored vector by the depth
    //      of the MacroVector.
    //   d. The maximal scoring difference is multiplied by the proportion of
    //      distance.
    if (!isNaN(available_distance_eq1)) {
        n_existing_lower = n_existing_lower + 1;
        percent_to_next_eq1_severity =
            current_severity_distance_eq1 / maxSeverity_eq1;
        normalized_severity_eq1 =
            available_distance_eq1 * percent_to_next_eq1_severity;
    }

    if (!isNaN(available_distance_eq2)) {
        n_existing_lower = n_existing_lower + 1;
        percent_to_next_eq2_severity =
            current_severity_distance_eq2 / maxSeverity_eq2;
        normalized_severity_eq2 =
            available_distance_eq2 * percent_to_next_eq2_severity;
    }

    if (!isNaN(available_distance_eq3eq6)) {
        n_existing_lower = n_existing_lower + 1;
        percent_to_next_eq3eq6_severity =
            current_severity_distance_eq3eq6 / maxSeverity_eq3eq6;
        normalized_severity_eq3eq6 =
            available_distance_eq3eq6 * percent_to_next_eq3eq6_severity;
    }

    if (!isNaN(available_distance_eq4)) {
        n_existing_lower = n_existing_lower + 1;
        percent_to_next_eq4_severity =
            current_severity_distance_eq4 / maxSeverity_eq4;
        normalized_severity_eq4 =
            available_distance_eq4 * percent_to_next_eq4_severity;
    }

    if (!isNaN(available_distance_eq5)) {
        // for eq5 is always 0 the percentage
        n_existing_lower = n_existing_lower + 1;
        percent_to_next_eq5_severity = 0;
        normalized_severity_eq5 =
            available_distance_eq5 * percent_to_next_eq5_severity;
    }

    // 2. The mean of the above computed proportional distances is computed.
    let mean_distance;
    if (n_existing_lower == 0) {
        mean_distance = 0;
    } else {
        // sometimes we need to go up but there is nothing there, or down but there is nothing there so it's a change of 0.
        mean_distance =
            (normalized_severity_eq1 +
                normalized_severity_eq2 +
                normalized_severity_eq3eq6 +
                normalized_severity_eq4 +
                normalized_severity_eq5) /
            n_existing_lower;
    }

    // 3. The score of the vector is the score of the MacroVector
    //    (i.e. the score of the highest severity vector) minus the mean
    //    distance so computed. This score is rounded to one decimal place.
    value -= mean_distance;
    if (value < 0) {
        value = 0.0;
    }
    if (value > 10) {
        value = 10.0;
    }
    return Math.round(value * 10) / 10;
}

const maxComposed = {
    // EQ1
    eq1: {
        0: ["AV:N/PR:N/UI:N/"],
        1: ["AV:A/PR:N/UI:N/", "AV:N/PR:L/UI:N/", "AV:N/PR:N/UI:P/"],
        2: ["AV:P/PR:N/UI:N/", "AV:A/PR:L/UI:P/"],
    },
    // EQ2
    eq2: {
        0: ["AC:L/AT:N/"],
        1: ["AC:H/AT:N/", "AC:L/AT:P/"],
    },
    // EQ3+EQ6
    eq3: {
        0: {
            0: ["VC:H/VI:H/VA:H/CR:H/IR:H/AR:H/"],
            1: [
                "VC:H/VI:H/VA:L/CR:M/IR:M/AR:H/",
                "VC:H/VI:H/VA:H/CR:M/IR:M/AR:M/",
            ],
        },
        1: {
            0: [
                "VC:L/VI:H/VA:H/CR:H/IR:H/AR:H/",
                "VC:H/VI:L/VA:H/CR:H/IR:H/AR:H/",
            ],
            1: [
                "VC:L/VI:H/VA:L/CR:H/IR:M/AR:H/",
                "VC:L/VI:H/VA:H/CR:H/IR:M/AR:M/",
                "VC:H/VI:L/VA:H/CR:M/IR:H/AR:M/",
                "VC:H/VI:L/VA:L/CR:M/IR:H/AR:H/",
                "VC:L/VI:L/VA:H/CR:H/IR:H/AR:M/",
            ],
        },
        2: { 1: ["VC:L/VI:L/VA:L/CR:H/IR:H/AR:H/"] },
    },
    // EQ4
    eq4: {
        0: ["SC:H/SI:S/SA:S/"],
        1: ["SC:H/SI:H/SA:H/"],
        2: ["SC:L/SI:L/SA:L/"],
    },
    // EQ5
    eq5: {
        0: ["E:A/"],
        1: ["E:P/"],
        2: ["E:U/"],
    },
};

function getEQMaxes(lookup, eq) {
    return maxComposed["eq" + eq][lookup[eq - 1]];
}

function extractValueMetric(metric, str) {
    // indexOf gives first index of the metric, we then need to go over its size
    const extracted = str.slice(str.indexOf(metric) + metric.length + 1);
    // remove what follow
    if (extracted.indexOf("/") > 0) {
        return extracted.substring(0, extracted.indexOf("/"));
    } else {
        // case where it is the last metric so no ending /
        return extracted;
    }
}

function m(cvssSelected, metric) {
    const selected = cvssSelected[metric];

    // If E=X it will default to the worst case i.e. E=A
    if (metric == "E" && selected == "X") {
        return "A";
    }
    // If CR=X, IR=X or AR=X they will default to the worst case i.e. CR=H, IR=H and AR=H
    if (metric == "CR" && selected == "X") {
        return "H";
    }
    // IR:X is the same as IR:H
    if (metric == "IR" && selected == "X") {
        return "H";
    }
    // AR:X is the same as AR:H
    if (metric == "AR" && selected == "X") {
        return "H";
    }

    // All other environmental metrics just overwrite base score values,
    // so if they’re not defined just use the base score value.
    if (cvssSelected["M" + metric]) {
        const modified_selected = cvssSelected["M" + metric];
        if (modified_selected != "X") {
            return modified_selected;
        }
    }

    return selected;
}

function macroVector(cvssSelected) {
    // EQ1: 0-AV:N and PR:N and UI:N
    //      1-(AV:N or PR:N or UI:N) and not (AV:N and PR:N and UI:N) and not AV:P
    //      2-AV:P or not(AV:N or PR:N or UI:N)

    let eq1;
    if (
        m(cvssSelected, "AV") == "N" &&
        m(cvssSelected, "PR") == "N" &&
        m(cvssSelected, "UI") == "N"
    ) {
        eq1 = "0";
    } else if (
        (m(cvssSelected, "AV") == "N" ||
            m(cvssSelected, "PR") == "N" ||
            m(cvssSelected, "UI") == "N") &&
        !(
            m(cvssSelected, "AV") == "N" &&
            m(cvssSelected, "PR") == "N" &&
            m(cvssSelected, "UI") == "N"
        ) &&
        !(m(cvssSelected, "AV") == "P")
    ) {
        eq1 = "1";
    } else if (
        m(cvssSelected, "AV") == "P" ||
        !(
            m(cvssSelected, "AV") == "N" ||
            m(cvssSelected, "PR") == "N" ||
            m(cvssSelected, "UI") == "N"
        )
    ) {
        eq1 = "2";
    }

    // EQ2: 0-(AC:L and AT:N)
    //      1-(not(AC:L and AT:N))

    let eq2;
    if (m(cvssSelected, "AC") == "L" && m(cvssSelected, "AT") == "N") {
        eq2 = "0";
    } else if (
        !(m(cvssSelected, "AC") == "L" && m(cvssSelected, "AT") == "N")
    ) {
        eq2 = "1";
    }

    // EQ3: 0-(VC:H and VI:H)
    //      1-(not(VC:H and VI:H) and (VC:H or VI:H or VA:H))
    //      2-not (VC:H or VI:H or VA:H)
    let eq3;
    if (m(cvssSelected, "VC") == "H" && m(cvssSelected, "VI") == "H") {
        eq3 = 0;
    } else if (
        !(m(cvssSelected, "VC") == "H" && m(cvssSelected, "VI") == "H") &&
        (m(cvssSelected, "VC") == "H" ||
            m(cvssSelected, "VI") == "H" ||
            m(cvssSelected, "VA") == "H")
    ) {
        eq3 = 1;
    } else if (
        !(
            m(cvssSelected, "VC") == "H" ||
            m(cvssSelected, "VI") == "H" ||
            m(cvssSelected, "VA") == "H"
        )
    ) {
        eq3 = 2;
    }

    // EQ4: 0-(MSI:S or MSA:S)
    //      1-not (MSI:S or MSA:S) and (SC:H or SI:H or SA:H)
    //      2-not (MSI:S or MSA:S) and not (SC:H or SI:H or SA:H)

    let eq4;
    if (m(cvssSelected, "MSI") == "S" || m(cvssSelected, "MSA") == "S") {
        eq4 = 0;
    } else if (
        !(m(cvssSelected, "MSI") == "S" || m(cvssSelected, "MSA") == "S") &&
        (m(cvssSelected, "SC") == "H" ||
            m(cvssSelected, "SI") == "H" ||
            m(cvssSelected, "SA") == "H")
    ) {
        eq4 = 1;
    } else if (
        !(m(cvssSelected, "MSI") == "S" || m(cvssSelected, "MSA") == "S") &&
        !(
            m(cvssSelected, "SC") == "H" ||
            m(cvssSelected, "SI") == "H" ||
            m(cvssSelected, "SA") == "H"
        )
    ) {
        eq4 = 2;
    }

    // EQ5: 0-E:A
    //      1-E:P
    //      2-E:U
    let eq5;
    if (m(cvssSelected, "E") == "A") {
        eq5 = 0;
    } else if (m(cvssSelected, "E") == "P") {
        eq5 = 1;
    } else if (m(cvssSelected, "E") == "U") {
        eq5 = 2;
    }

    // EQ6: 0-(CR:H and VC:H) or (IR:H and VI:H) or (AR:H and VA:H)
    //      1-not[(CR:H and VC:H) or (IR:H and VI:H) or (AR:H and VA:H)]
    let eq6;
    if (
        (m(cvssSelected, "CR") == "H" && m(cvssSelected, "VC") == "H") ||
        (m(cvssSelected, "IR") == "H" && m(cvssSelected, "VI") == "H") ||
        (m(cvssSelected, "AR") == "H" && m(cvssSelected, "VA") == "H")
    ) {
        eq6 = 0;
    } else if (
        !(
            (m(cvssSelected, "CR") == "H" && m(cvssSelected, "VC") == "H") ||
            (m(cvssSelected, "IR") == "H" && m(cvssSelected, "VI") == "H") ||
            (m(cvssSelected, "AR") == "H" && m(cvssSelected, "VA") == "H")
        )
    ) {
        eq6 = 1;
    }

    return eq1 + eq2 + eq3 + eq4 + eq5 + eq6;
}

const cvssLookup_global = {
    "000000": 10,
    "000001": 9.9,
    "000010": 9.8,
    "000011": 9.5,
    "000020": 9.5,
    "000021": 9.2,
    "000100": 10,
    "000101": 9.6,
    "000110": 9.3,
    "000111": 8.7,
    "000120": 9.1,
    "000121": 8.1,
    "000200": 9.3,
    "000201": 9,
    "000210": 8.9,
    "000211": 8,
    "000220": 8.1,
    "000221": 6.8,
    "001000": 9.8,
    "001001": 9.5,
    "001010": 9.5,
    "001011": 9.2,
    "001020": 9,
    "001021": 8.4,
    "001100": 9.3,
    "001101": 9.2,
    "001110": 8.9,
    "001111": 8.1,
    "001120": 8.1,
    "001121": 6.5,
    "001200": 8.8,
    "001201": 8,
    "001210": 7.8,
    "001211": 7,
    "001220": 6.9,
    "001221": 4.8,
    "002001": 9.2,
    "002011": 8.2,
    "002021": 7.2,
    "002101": 7.9,
    "002111": 6.9,
    "002121": 5,
    "002201": 6.9,
    "002211": 5.5,
    "002221": 2.7,
    "010000": 9.9,
    "010001": 9.7,
    "010010": 9.5,
    "010011": 9.2,
    "010020": 9.2,
    "010021": 8.5,
    "010100": 9.5,
    "010101": 9.1,
    "010110": 9,
    "010111": 8.3,
    "010120": 8.4,
    "010121": 7.1,
    "010200": 9.2,
    "010201": 8.1,
    "010210": 8.2,
    "010211": 7.1,
    "010220": 7.2,
    "010221": 5.3,
    "011000": 9.5,
    "011001": 9.3,
    "011010": 9.2,
    "011011": 8.5,
    "011020": 8.5,
    "011021": 7.3,
    "011100": 9.2,
    "011101": 8.2,
    "011110": 8,
    "011111": 7.2,
    "011120": 7,
    "011121": 5.9,
    "011200": 8.4,
    "011201": 7,
    "011210": 7.1,
    "011211": 5.2,
    "011220": 5,
    "011221": 3,
    "012001": 8.6,
    "012011": 7.5,
    "012021": 5.2,
    "012101": 7.1,
    "012111": 5.2,
    "012121": 2.9,
    "012201": 6.3,
    "012211": 2.9,
    "012221": 1.7,
    100000: 9.8,
    100001: 9.5,
    100010: 9.4,
    100011: 8.7,
    100020: 9.1,
    100021: 8.1,
    100100: 9.4,
    100101: 8.9,
    100110: 8.6,
    100111: 7.4,
    100120: 7.7,
    100121: 6.4,
    100200: 8.7,
    100201: 7.5,
    100210: 7.4,
    100211: 6.3,
    100220: 6.3,
    100221: 4.9,
    101000: 9.4,
    101001: 8.9,
    101010: 8.8,
    101011: 7.7,
    101020: 7.6,
    101021: 6.7,
    101100: 8.6,
    101101: 7.6,
    101110: 7.4,
    101111: 5.8,
    101120: 5.9,
    101121: 5,
    101200: 7.2,
    101201: 5.7,
    101210: 5.7,
    101211: 5.2,
    101220: 5.2,
    101221: 2.5,
    102001: 8.3,
    102011: 7,
    102021: 5.4,
    102101: 6.5,
    102111: 5.8,
    102121: 2.6,
    102201: 5.3,
    102211: 2.1,
    102221: 1.3,
    110000: 9.5,
    110001: 9,
    110010: 8.8,
    110011: 7.6,
    110020: 7.6,
    110021: 7,
    110100: 9,
    110101: 7.7,
    110110: 7.5,
    110111: 6.2,
    110120: 6.1,
    110121: 5.3,
    110200: 7.7,
    110201: 6.6,
    110210: 6.8,
    110211: 5.9,
    110220: 5.2,
    110221: 3,
    111000: 8.9,
    111001: 7.8,
    111010: 7.6,
    111011: 6.7,
    111020: 6.2,
    111021: 5.8,
    111100: 7.4,
    111101: 5.9,
    111110: 5.7,
    111111: 5.7,
    111120: 4.7,
    111121: 2.3,
    111200: 6.1,
    111201: 5.2,
    111210: 5.7,
    111211: 2.9,
    111220: 2.4,
    111221: 1.6,
    112001: 7.1,
    112011: 5.9,
    112021: 3,
    112101: 5.8,
    112111: 2.6,
    112121: 1.5,
    112201: 2.3,
    112211: 1.3,
    112221: 0.6,
    200000: 9.3,
    200001: 8.7,
    200010: 8.6,
    200011: 7.2,
    200020: 7.5,
    200021: 5.8,
    200100: 8.6,
    200101: 7.4,
    200110: 7.4,
    200111: 6.1,
    200120: 5.6,
    200121: 3.4,
    200200: 7,
    200201: 5.4,
    200210: 5.2,
    200211: 4,
    200220: 4,
    200221: 2.2,
    201000: 8.5,
    201001: 7.5,
    201010: 7.4,
    201011: 5.5,
    201020: 6.2,
    201021: 5.1,
    201100: 7.2,
    201101: 5.7,
    201110: 5.5,
    201111: 4.1,
    201120: 4.6,
    201121: 1.9,
    201200: 5.3,
    201201: 3.6,
    201210: 3.4,
    201211: 1.9,
    201220: 1.9,
    201221: 0.8,
    202001: 6.4,
    202011: 5.1,
    202021: 2,
    202101: 4.7,
    202111: 2.1,
    202121: 1.1,
    202201: 2.4,
    202211: 0.9,
    202221: 0.4,
    210000: 8.8,
    210001: 7.5,
    210010: 7.3,
    210011: 5.3,
    210020: 6,
    210021: 5,
    210100: 7.3,
    210101: 5.5,
    210110: 5.9,
    210111: 4,
    210120: 4.1,
    210121: 2,
    210200: 5.4,
    210201: 4.3,
    210210: 4.5,
    210211: 2.2,
    210220: 2,
    210221: 1.1,
    211000: 7.5,
    211001: 5.5,
    211010: 5.8,
    211011: 4.5,
    211020: 4,
    211021: 2.1,
    211100: 6.1,
    211101: 5.1,
    211110: 4.8,
    211111: 1.8,
    211120: 2,
    211121: 0.9,
    211200: 4.6,
    211201: 1.8,
    211210: 1.7,
    211211: 0.7,
    211220: 0.8,
    211221: 0.2,
    212001: 5.3,
    212011: 2.4,
    212021: 1.4,
    212101: 2.4,
    212111: 1.2,
    212121: 0.5,
    212201: 1,
    212211: 0.3,
    212221: 0.1,
};

const maxSeverity = {
    eq1: {
        0: 1,
        1: 4,
        2: 5,
    },
    eq2: {
        0: 1,
        1: 2,
    },
    eq3eq6: {
        0: { 0: 7, 1: 6 },
        1: { 0: 8, 1: 8 },
        2: { 1: 10 },
    },
    eq4: {
        0: 6,
        1: 5,
        2: 4,
    },
    eq5: {
        0: 1,
        1: 1,
        2: 1,
    },
};
