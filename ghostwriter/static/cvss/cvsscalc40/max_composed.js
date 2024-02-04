// Copyright FIRST, Red Hat, and contributors
// SPDX-License-Identifier: BSD-2-Clause

maxComposed = {
	// EQ1
	"eq1": {
		0: ["AV:N/PR:N/UI:N/"],
		1: ["AV:A/PR:N/UI:N/", "AV:N/PR:L/UI:N/", "AV:N/PR:N/UI:P/"],
		2: ["AV:P/PR:N/UI:N/", "AV:A/PR:L/UI:P/"]
	},
	// EQ2
	"eq2": {
		0: ["AC:L/AT:N/"],
		1: ["AC:H/AT:N/", "AC:L/AT:P/"]
	},
	// EQ3+EQ6
	"eq3": {
		0: { "0": ["VC:H/VI:H/VA:H/CR:H/IR:H/AR:H/"], "1": ["VC:H/VI:H/VA:L/CR:M/IR:M/AR:H/", "VC:H/VI:H/VA:H/CR:M/IR:M/AR:M/"] },
		1: { "0": ["VC:L/VI:H/VA:H/CR:H/IR:H/AR:H/", "VC:H/VI:L/VA:H/CR:H/IR:H/AR:H/"], "1": ["VC:L/VI:H/VA:L/CR:H/IR:M/AR:H/", "VC:L/VI:H/VA:H/CR:H/IR:M/AR:M/", "VC:H/VI:L/VA:H/CR:M/IR:H/AR:M/", "VC:H/VI:L/VA:L/CR:M/IR:H/AR:H/", "VC:L/VI:L/VA:H/CR:H/IR:H/AR:M/"] },
		2: { "1": ["VC:L/VI:L/VA:L/CR:H/IR:H/AR:H/"] },
	},
	// EQ4
	"eq4": {
		0: ["SC:H/SI:S/SA:S/"],
		1: ["SC:H/SI:H/SA:H/"],
		2: ["SC:L/SI:L/SA:L/"]

	},
	// EQ5
	"eq5": {
		0: ["E:A/"],
		1: ["E:P/"],
		2: ["E:U/"],
	},
}
