// Copyright FIRST, Red Hat, and contributors
// SPDX-License-Identifier: BSD-2-Clause

const app = Vue.createApp({
    data() {
        return {
            cvssConfigData: cvssConfig,
            maxComposedData: maxComposed,
            maxSeverityData: maxSeverity,
            expectedMetricOrder: expectedMetricOrder,
            cvssMacroVectorDetailsData: cvssMacroVectorDetails,
            cvssMacroVectorValuesData: cvssMacroVectorValues,
            showDetails: false,
            cvssSelected: null,
            header_height: 0,
            lookup: cvssLookup_global,
        }
    },
    methods: {
        getEQMaxes(lookup, eq) {
            return maxComposed["eq" + eq][lookup[eq - 1]]
        },
        extractValueMetric(metric, str) {
            // indexOf gives first index of the metric, we then need to go over its size
            extracted = str.slice(str.indexOf(metric) + metric.length + 1)
            // remove what follow
            if (extracted.indexOf('/') > 0) {
                metric_val = extracted.substring(0, extracted.indexOf('/'));
            }
            else {
                // case where it is the last metric so no ending /
                metric_val = extracted
            }
            return metric_val
        },
        buttonClass(isPrimary, big = false) {
            result = "btn btn-m"
            if (isPrimary) {
                result += " btn-primary"
            }
            if (!big) {
                result += " btn-sm"
            }

            return result
        },
        scoreClass(qualScore) {
            if (qualScore == "Low") {
                return "c-hand text-success"
            }
            else if (qualScore == "Medium") {
                return "c-hand text-warning"
            }
            else if (qualScore == "High") {
                return "c-hand text-error"
            }
            else if (qualScore == "Critical") {
                return "c-hand text-error text-bold"
            }
            else {
                return "c-hand text-gray"
            }
        },
        copyVector() {
            navigator.clipboard.writeText(this.vector)
            window.location.hash = this.vector
        },
        onButton(metric, value) {
            this.cvssSelected[metric] = value
            window.location.hash = this.vector
        },
        setButtonsToVector(vector) {
            this.resetSelected()
            metrics = vector.split("/")
            // Remove hash + CVSS v4.0 prefix
            metrics.shift()

            // Ensure compliance first
            toSelect = {}
            oi = 0
            for (index in metrics) {
                [key, value] = metrics[index].split(":")

                expected = Object.entries(this.expectedMetricOrder)[oi++]
                while (true) {
                    // If out of possible metrics ordering, it not a valid value thus
                    // the vector is invalid
                    if (expected == undefined) {
                        console.log("Error invalid vector, too many metric values")
                        return
                    }
                    if (key != expected[0]) {
                        // If not this metric but is mandatory, the vector is invalid
                        // As the only mandatory ones are from the Base group, 11 is the
                        // number of metrics part of it.
                        if (oi <= 11) {
                            console.log("Error invalid vector, missing mandatory metrics")
                            return
                        }
                        // If a non-mandatory, retry
                        expected = Object.entries(this.expectedMetricOrder)[oi++]
                        continue
                    }
                    break
                }
                // The value MUST be part of the metric's values, case insensitive
                if (!expected[1].includes(value)) {
                    console.log("Error invalid vector, for key " + key + ", value " + value + " is not in " + expected[1])
                    return
                }
                if (key in this.cvssSelected) {
                    toSelect[key] = value
                }
            }

            // Apply iff is compliant
            for (key in toSelect) {
                this.cvssSelected[key] = toSelect[key]
            }
        },
        m(metric) {
            selected = this.cvssSelected[metric]

            // If E=X it will default to the worst case i.e. E=A
            if (metric == "E" && selected == "X") {
                return "A"
            }
            // If CR=X, IR=X or AR=X they will default to the worst case i.e. CR=H, IR=H and AR=H
            if (metric == "CR" && selected == "X") {
                return "H";
            }
            // IR:X is the same as IR:H
            if (metric == "IR" && selected == "X") {
                return "H"
            }
            // AR:X is the same as AR:H
            if (metric == "AR" && selected == "X") {
                return "H"
            }

            // All other environmental metrics just overwrite base score values,
            // so if they’re not defined just use the base score value.
            if (Object.keys(this.cvssSelected).includes("M" + metric)) {
                modified_selected = this.cvssSelected["M" + metric]
                if (modified_selected != "X") {
                    return modified_selected
                }
            }

            return selected
        },
        onReset() {
            window.location.hash = ""
        },
        resetSelected() {
            this.cvssSelected = {}
            for ([metricType, metricTypeData] of Object.entries(this.cvssConfigData)) {
                for ([metricGroup, metricGroupData] of Object.entries(metricTypeData.metric_groups)) {
                    for ([metric, metricData] of Object.entries(metricGroupData)) {
                        this.cvssSelected[metricData.short] = metricData.selected
                    }
                }
            }
        },
        splitObjectEntries(object, chunkSize) {
            arr = Object.entries(object)
            res = [];
            for (let i = 0; i < arr.length; i += chunkSize) {
                chunk = arr.slice(i, i + chunkSize)
                res.push(chunk)
            }
            return res
        }
    },
    computed: {
        vector() {
            value = "CVSS:4.0"
            for (metric in this.expectedMetricOrder) {
                selected = this.cvssSelected[metric]
                if (selected != "X") {
                    value = value.concat("/" + metric + ":" + selected)
                }
            }
            return value
        },
        macroVector() {
            // EQ1: 0-AV:N and PR:N and UI:N
            //      1-(AV:N or PR:N or UI:N) and not (AV:N and PR:N and UI:N) and not AV:P
            //      2-AV:P or not(AV:N or PR:N or UI:N)

            if (this.m("AV") == "N" && this.m("PR") == "N" && this.m("UI") == "N") {
                eq1 = "0"
            }
            else if ((this.m("AV") == "N" || this.m("PR") == "N" || this.m("UI") == "N")
                && !(this.m("AV") == "N" && this.m("PR") == "N" && this.m("UI") == "N")
                && !(this.m("AV") == "P")) {
                eq1 = "1"
            }
            else if (this.m("AV") == "P"
                || !(this.m("AV") == "N" || this.m("PR") == "N" || this.m("UI") == "N")) {
                eq1 = "2"
            }

            // EQ2: 0-(AC:L and AT:N)
            //      1-(not(AC:L and AT:N))

            if (this.m("AC") == "L" && this.m("AT") == "N") {
                eq2 = "0"
            }
            else if (!(this.m("AC") == "L" && this.m("AT") == "N")) {
                eq2 = "1"
            }

            // EQ3: 0-(VC:H and VI:H)
            //      1-(not(VC:H and VI:H) and (VC:H or VI:H or VA:H))
            //      2-not (VC:H or VI:H or VA:H)
            if (this.m("VC") == "H" && this.m("VI") == "H") {
                eq3 = 0
            }
            else if (!(this.m("VC") == "H" && this.m("VI") == "H")
                && (this.m("VC") == "H" || this.m("VI") == "H" || this.m("VA") == "H")) {
                eq3 = 1
            }
            else if (!(this.m("VC") == "H" || this.m("VI") == "H" || this.m("VA") == "H")) {
                eq3 = 2
            }

            // EQ4: 0-(MSI:S or MSA:S)
            //      1-not (MSI:S or MSA:S) and (SC:H or SI:H or SA:H)
            //      2-not (MSI:S or MSA:S) and not (SC:H or SI:H or SA:H)

            if (this.m("MSI") == "S" || this.m("MSA") == "S") {
                eq4 = 0
            }
            else if (!(this.m("MSI") == "S" || this.m("MSA") == "S") &&
                (this.m("SC") == "H" || this.m("SI") == "H" || this.m("SA") == "H")) {
                eq4 = 1
            }
            else if (!(this.m("MSI") == "S" || this.m("MSA") == "S") &&
                !((this.m("SC") == "H" || this.m("SI") == "H" || this.m("SA") == "H"))) {
                eq4 = 2
            }

            // EQ5: 0-E:A
            //      1-E:P
            //      2-E:U

            if (this.m("E") == "A") {
                eq5 = 0
            }
            else if (this.m("E") == "P") {
                eq5 = 1
            }
            else if (this.m("E") == "U") {
                eq5 = 2
            }

            // EQ6: 0-(CR:H and VC:H) or (IR:H and VI:H) or (AR:H and VA:H)
            //      1-not[(CR:H and VC:H) or (IR:H and VI:H) or (AR:H and VA:H)]

            if ((this.m("CR") == "H" && this.m("VC") == "H")
                || (this.m("IR") == "H" && this.m("VI") == "H")
                || (this.m("AR") == "H" && this.m("VA") == "H")) {
                eq6 = 0
            }
            else if (!((this.m("CR") == "H" && this.m("VC") == "H")
                || (this.m("IR") == "H" && this.m("VI") == "H")
                || (this.m("AR") == "H" && this.m("VA") == "H"))) {
                eq6 = 1
            }

            return eq1 + eq2 + eq3 + eq4 + eq5 + eq6
        },
        score() {
            // The following defines the index of each metric's values.
            // It is used when looking for the highest vector part of the
            // combinations produced by the MacroVector respective highest vectors.
            AV_levels = { "N": 0.0, "A": 0.1, "L": 0.2, "P": 0.3 }
            PR_levels = { "N": 0.0, "L": 0.1, "H": 0.2 }
            UI_levels = { "N": 0.0, "P": 0.1, "A": 0.2 }

            AC_levels = { 'L': 0.0, 'H': 0.1 }
            AT_levels = { 'N': 0.0, 'P': 0.1 }

            VC_levels = { 'H': 0.0, 'L': 0.1, 'N': 0.2 }
            VI_levels = { 'H': 0.0, 'L': 0.1, 'N': 0.2 }
            VA_levels = { 'H': 0.0, 'L': 0.1, 'N': 0.2 }

            SC_levels = { 'H': 0.1, 'L': 0.2, 'N': 0.3 }
            SI_levels = { 'S': 0.0, 'H': 0.1, 'L': 0.2, 'N': 0.3 }
            SA_levels = { 'S': 0.0, 'H': 0.1, 'L': 0.2, 'N': 0.3 }

            CR_levels = { 'H': 0.0, 'M': 0.1, 'L': 0.2 }
            IR_levels = { 'H': 0.0, 'M': 0.1, 'L': 0.2 }
            AR_levels = { 'H': 0.0, 'M': 0.1, 'L': 0.2 }

            E_levels = { 'U': 0.2, 'P': 0.1, 'A': 0 }



            macroVector = this.macroVector

            // Exception for no impact on system (shortcut)
            if (["VC", "VI", "VA", "SC", "SI", "SA"].every((metric) => this.m(metric) == "N")) {
                return 0.0
            }
            value = this.lookup[macroVector]

            // 1. For each of the EQs:
            //   a. The maximal scoring difference is determined as the difference
            //      between the current MacroVector and the lower MacroVector.
            //     i. If there is no lower MacroVector the available distance is
            //        set to NaN and then ignored in the further calculations.
            eq1_val = parseInt(macroVector[0])
            eq2_val = parseInt(macroVector[1])
            eq3_val = parseInt(macroVector[2])
            eq4_val = parseInt(macroVector[3])
            eq5_val = parseInt(macroVector[4])
            eq6_val = parseInt(macroVector[5])

            // compute next lower macro, it can also not exist
            eq1_next_lower_macro = "".concat(eq1_val + 1, eq2_val, eq3_val, eq4_val, eq5_val, eq6_val)
            eq2_next_lower_macro = "".concat(eq1_val, eq2_val + 1, eq3_val, eq4_val, eq5_val, eq6_val)

            // eq3 and eq6 are related
            if (eq3 == 1 && eq6 == 1) {
                // 11 --> 21
                eq3eq6_next_lower_macro = "".concat(eq1_val, eq2_val, eq3_val + 1, eq4_val, eq5_val, eq6_val)
            }
            else if (eq3 == 0 && eq6 == 1) {
                // 01 --> 11
                eq3eq6_next_lower_macro = "".concat(eq1_val, eq2_val, eq3_val + 1, eq4_val, eq5_val, eq6_val)
            }
            else if (eq3 == 1 && eq6 == 0) {
                // 10 --> 11
                eq3eq6_next_lower_macro = "".concat(eq1_val, eq2_val, eq3_val, eq4_val, eq5_val, eq6_val + 1)
            }
            else if (eq3 == 0 && eq6 == 0) {
                // 00 --> 01
                // 00 --> 10
                eq3eq6_next_lower_macro_left = "".concat(eq1_val, eq2_val, eq3_val, eq4_val, eq5_val, eq6_val + 1)
                eq3eq6_next_lower_macro_right = "".concat(eq1_val, eq2_val, eq3_val + 1, eq4_val, eq5_val, eq6_val)
            }
            else {
                // 21 --> 32 (do not exist)
                eq3eq6_next_lower_macro = "".concat(eq1_val, eq2_val, eq3_val + 1, eq4_val, eq5_val, eq6_val + 1)
            }


            eq4_next_lower_macro = "".concat(eq1_val, eq2_val, eq3_val, eq4_val + 1, eq5_val, eq6_val)
            eq5_next_lower_macro = "".concat(eq1_val, eq2_val, eq3_val, eq4_val, eq5_val + 1, eq6_val)


            // get their score, if the next lower macro score do not exist the result is NaN
            score_eq1_next_lower_macro = this.lookup[eq1_next_lower_macro]
            score_eq2_next_lower_macro = this.lookup[eq2_next_lower_macro]

            if (eq3 == 0 && eq6 == 0) {
                // multiple path take the one with higher score
                score_eq3eq6_next_lower_macro_left = this.lookup[eq3eq6_next_lower_macro_left]
                score_eq3eq6_next_lower_macro_right = this.lookup[eq3eq6_next_lower_macro_right]

                if (score_eq3eq6_next_lower_macro_left > score_eq3eq6_next_lower_macro_right) {
                    score_eq3eq6_next_lower_macro = score_eq3eq6_next_lower_macro_left
                }
                else {
                    score_eq3eq6_next_lower_macro = score_eq3eq6_next_lower_macro_right
                }
            }
            else {
                score_eq3eq6_next_lower_macro = this.lookup[eq3eq6_next_lower_macro]
            }


            score_eq4_next_lower_macro = this.lookup[eq4_next_lower_macro]
            score_eq5_next_lower_macro = this.lookup[eq5_next_lower_macro]

            //   b. The severity distance of the to-be scored vector from a
            //      highest severity vector in the same MacroVector is determined.
            eq1_maxes = this.getEQMaxes(macroVector, 1)
            eq2_maxes = this.getEQMaxes(macroVector, 2)
            eq3_eq6_maxes = this.getEQMaxes(macroVector, 3)[macroVector[5]]
            eq4_maxes = this.getEQMaxes(macroVector, 4)
            eq5_maxes = this.getEQMaxes(macroVector, 5)

            // compose them
            max_vectors = []
            for (eq1_max of eq1_maxes) {
                for (eq2_max of eq2_maxes) {
                    for (eq3_eq6_max of eq3_eq6_maxes) {
                        for (eq4_max of eq4_maxes) {
                            for (eq5max of eq5_maxes) {
                                max_vectors.push(eq1_max + eq2_max + eq3_eq6_max + eq4_max + eq5max)
                            }
                        }
                    }
                }
            }

            // Find the max vector to use i.e. one in the combination of all the highests
            // that is greater or equal (severity distance) than the to-be scored vector.
            for (let i = 0; i < max_vectors.length; i++) {
                max_vector = max_vectors[i]
                severity_distance_AV = AV_levels[this.m("AV")] - AV_levels[this.extractValueMetric("AV", max_vector)]
                severity_distance_PR = PR_levels[this.m("PR")] - PR_levels[this.extractValueMetric("PR", max_vector)]
                severity_distance_UI = UI_levels[this.m("UI")] - UI_levels[this.extractValueMetric("UI", max_vector)]

                severity_distance_AC = AC_levels[this.m("AC")] - AC_levels[this.extractValueMetric("AC", max_vector)]
                severity_distance_AT = AT_levels[this.m("AT")] - AT_levels[this.extractValueMetric("AT", max_vector)]

                severity_distance_VC = VC_levels[this.m("VC")] - VC_levels[this.extractValueMetric("VC", max_vector)]
                severity_distance_VI = VI_levels[this.m("VI")] - VI_levels[this.extractValueMetric("VI", max_vector)]
                severity_distance_VA = VA_levels[this.m("VA")] - VA_levels[this.extractValueMetric("VA", max_vector)]

                severity_distance_SC = SC_levels[this.m("SC")] - SC_levels[this.extractValueMetric("SC", max_vector)]
                severity_distance_SI = SI_levels[this.m("SI")] - SI_levels[this.extractValueMetric("SI", max_vector)]
                severity_distance_SA = SA_levels[this.m("SA")] - SA_levels[this.extractValueMetric("SA", max_vector)]

                severity_distance_CR = CR_levels[this.m("CR")] - CR_levels[this.extractValueMetric("CR", max_vector)]
                severity_distance_IR = IR_levels[this.m("IR")] - IR_levels[this.extractValueMetric("IR", max_vector)]
                severity_distance_AR = AR_levels[this.m("AR")] - AR_levels[this.extractValueMetric("AR", max_vector)]


                // if any is less than zero this is not the right max
                if ([severity_distance_AV, severity_distance_PR, severity_distance_UI, severity_distance_AC, severity_distance_AT, severity_distance_VC, severity_distance_VI, severity_distance_VA, severity_distance_SC, severity_distance_SI, severity_distance_SA, severity_distance_CR, severity_distance_IR, severity_distance_AR].some((met) => met < 0)) {
                    continue
                }
                // if multiple maxes exist to reach it it is enough the first one
                break
            }

            current_severity_distance_eq1 = severity_distance_AV + severity_distance_PR + severity_distance_UI
            current_severity_distance_eq2 = severity_distance_AC + severity_distance_AT
            current_severity_distance_eq3eq6 = severity_distance_VC + severity_distance_VI + severity_distance_VA + severity_distance_CR + severity_distance_IR + severity_distance_AR
            current_severity_distance_eq4 = severity_distance_SC + severity_distance_SI + severity_distance_SA
            current_severity_distance_eq5 = 0

            step = 0.1

            // if the next lower macro score do not exist the result is Nan
            // Rename to maximal scoring difference (aka MSD)
            available_distance_eq1 = value - score_eq1_next_lower_macro
            available_distance_eq2 = value - score_eq2_next_lower_macro
            available_distance_eq3eq6 = value - score_eq3eq6_next_lower_macro
            available_distance_eq4 = value - score_eq4_next_lower_macro
            available_distance_eq5 = value - score_eq5_next_lower_macro

            percent_to_next_eq1_severity = 0
            percent_to_next_eq2_severity = 0
            percent_to_next_eq3eq6_severity = 0
            percent_to_next_eq4_severity = 0
            percent_to_next_eq5_severity = 0

            // some of them do not exist, we will find them by retrieving the score. If score null then do not exist
            n_existing_lower = 0

            normalized_severity_eq1 = 0
            normalized_severity_eq2 = 0
            normalized_severity_eq3eq6 = 0
            normalized_severity_eq4 = 0
            normalized_severity_eq5 = 0

            // multiply by step because distance is pure
            maxSeverity_eq1 = this.maxSeverityData["eq1"][eq1_val] * step
            maxSeverity_eq2 = this.maxSeverityData["eq2"][eq2_val] * step
            maxSeverity_eq3eq6 = this.maxSeverityData["eq3eq6"][eq3_val][eq6_val] * step
            maxSeverity_eq4 = this.maxSeverityData["eq4"][eq4_val] * step

            //   c. The proportion of the distance is determined by dividing
            //      the severity distance of the to-be-scored vector by the depth
            //      of the MacroVector.
            //   d. The maximal scoring difference is multiplied by the proportion of
            //      distance.
            if (!isNaN(available_distance_eq1)) {
                n_existing_lower = n_existing_lower + 1
                percent_to_next_eq1_severity = (current_severity_distance_eq1) / maxSeverity_eq1
                normalized_severity_eq1 = available_distance_eq1 * percent_to_next_eq1_severity
            }

            if (!isNaN(available_distance_eq2)) {
                n_existing_lower = n_existing_lower + 1
                percent_to_next_eq2_severity = (current_severity_distance_eq2) / maxSeverity_eq2
                normalized_severity_eq2 = available_distance_eq2 * percent_to_next_eq2_severity
            }

            if (!isNaN(available_distance_eq3eq6)) {
                n_existing_lower = n_existing_lower + 1
                percent_to_next_eq3eq6_severity = (current_severity_distance_eq3eq6) / maxSeverity_eq3eq6
                normalized_severity_eq3eq6 = available_distance_eq3eq6 * percent_to_next_eq3eq6_severity
            }

            if (!isNaN(available_distance_eq4)) {
                n_existing_lower = n_existing_lower + 1
                percent_to_next_eq4_severity = (current_severity_distance_eq4) / maxSeverity_eq4
                normalized_severity_eq4 = available_distance_eq4 * percent_to_next_eq4_severity
            }

            if (!isNaN(available_distance_eq5)) {
                // for eq5 is always 0 the percentage
                n_existing_lower = n_existing_lower + 1
                percent_to_next_eq5_severity = 0
                normalized_severity_eq5 = available_distance_eq5 * percent_to_next_eq5_severity
            }

            // 2. The mean of the above computed proportional distances is computed.
            if (n_existing_lower == 0) {
                mean_distance = 0
            } else { // sometimes we need to go up but there is nothing there, or down but there is nothing there so it's a change of 0.
                mean_distance = (normalized_severity_eq1 + normalized_severity_eq2 + normalized_severity_eq3eq6 + normalized_severity_eq4 + normalized_severity_eq5) / n_existing_lower
            }

            // 3. The score of the vector is the score of the MacroVector
            //    (i.e. the score of the highest severity vector) minus the mean
            //    distance so computed. This score is rounded to one decimal place.
            value -= mean_distance;
            if (value < 0) {
                value = 0.0
            }
            if (value > 10) {
                value = 10.0
            }
            return value.toFixed(1)
        },
        qualScore() {
            if (this.score == 0) {
                return "None"
            }
            else if (this.score < 4.0) {
                return "Low"
            }
            else if (this.score < 7.0) {
                return "Medium"
            }
            else if (this.score < 9.0) {
                return "High"
            }
            else {
                return "Critical"
            }
        },
    },
    beforeMount() {
        this.resetSelected()
    },
    mounted() {
        this.setButtonsToVector(window.location.hash)
        window.addEventListener("hashchange", () => {
            this.setButtonsToVector(window.location.hash)
        })

        const resizeObserver = new ResizeObserver(() => {
            this.header_height = document.getElementById('header').clientHeight
        })

        resizeObserver.observe(document.getElementById('header'))
    }
})

app.mount("#app")
