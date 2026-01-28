/**
 * API client for fetching acronyms from the Ghostwriter backend
 */

import type { AcronymExpansion, AcronymMap } from "./text_expansion";

export interface DatabaseAcronym {
    id: number;
    acronym: string;
    expansion: string;
    is_active: boolean;
    priority: number;
    override_builtin: boolean;
    created_at: string | null;
    updated_at: string | null;
}

export interface GetAcronymsResponse {
    acronyms: DatabaseAcronym[];
}

/**
 * Fetch acronyms from the Ghostwriter API
 * @returns Promise resolving to acronyms map or null on error
 */
export async function fetchAcronymsFromAPI(): Promise<AcronymMap | null> {
    try {
        const response = await fetch("/api/getAcronyms", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                input: {
                    is_active: true, // Only fetch active acronyms
                },
            }),
            credentials: "same-origin", // Include cookies for auth
        });

        if (!response.ok) {
            console.warn(
                `Failed to fetch acronyms from API: ${response.status} ${response.statusText}`
            );
            return null;
        }

        const data: GetAcronymsResponse = await response.json();

        // Convert database format to AcronymMap format
        return convertDatabaseAcronymsToMap(data.acronyms);
    } catch (error) {
        console.error("Error fetching acronyms from API:", error);
        return null;
    }
}

/**
 * Convert database acronym array to AcronymMap structure
 * Groups acronyms by their acronym text and sorts by priority descending
 */
export function convertDatabaseAcronymsToMap(
    dbAcronyms: DatabaseAcronym[]
): AcronymMap {
    const map: AcronymMap = {};

    // Sort by priority descending (highest priority first)
    const sorted = [...dbAcronyms].sort((a, b) => b.priority - a.priority);

    for (const dbAcronym of sorted) {
        const { acronym, expansion } = dbAcronym;

        if (!map[acronym]) {
            map[acronym] = [];
        }

        map[acronym].push({
            full: expansion,
        });
    }

    return map;
}

/**
 * Merge database acronyms with bundled acronyms
 * Database acronyms with override_builtin=true replace bundled ones
 * Otherwise, database acronyms are added before bundled ones (higher priority)
 */
export function mergeAcronymMaps(
    dbMap: AcronymMap,
    builtinMap: AcronymMap,
    overrides: Set<string> = new Set()
): AcronymMap {
    const merged: AcronymMap = {};

    // Add all builtin acronyms first
    for (const [acronym, expansions] of Object.entries(builtinMap)) {
        // Skip if this acronym should be overridden
        if (!overrides.has(acronym)) {
            merged[acronym] = [...expansions];
        }
    }

    // Add database acronyms (prepend to give them priority)
    for (const [acronym, expansions] of Object.entries(dbMap)) {
        if (overrides.has(acronym)) {
            // Override: use only database expansions
            merged[acronym] = [...expansions];
        } else {
            // Merge: prepend database expansions
            if (!merged[acronym]) {
                merged[acronym] = [];
            }
            merged[acronym] = [...expansions, ...merged[acronym]];
        }
    }

    return merged;
}

/**
 * Fetch acronym overrides from the database
 * Returns set of acronym names that should override builtin definitions
 */
export async function fetchAcronymOverrides(): Promise<Set<string>> {
    try {
        const response = await fetch("/api/getAcronyms", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                input: {
                    is_active: true,
                },
            }),
            credentials: "same-origin",
        });

        if (!response.ok) {
            return new Set();
        }

        const data: GetAcronymsResponse = await response.json();

        // Extract acronyms with override_builtin=true
        const overrides = data.acronyms
            .filter((a) => a.override_builtin)
            .map((a) => a.acronym);

        return new Set(overrides);
    } catch (error) {
        console.error("Error fetching acronym overrides:", error);
        return new Set();
    }
}

/**
 * Initialize acronym data by fetching from API and merging with bundled data
 * Falls back to bundled data on error
 */
export async function initializeAcronymData(
    builtinMap: AcronymMap
): Promise<AcronymMap> {
    try {
        // Fetch both database acronyms and overrides
        const [dbMap, overrides] = await Promise.all([
            fetchAcronymsFromAPI(),
            fetchAcronymOverrides(),
        ]);

        if (!dbMap) {
            // API fetch failed, use builtin only
            console.info("Using builtin acronyms only (API fetch failed)");
            return builtinMap;
        }

        // Merge database and builtin acronyms
        const merged = mergeAcronymMaps(dbMap, builtinMap, overrides);
        console.info(
            `Loaded ${Object.keys(dbMap).length} acronyms from database, merged with ${Object.keys(builtinMap).length} builtin acronyms`
        );
        return merged;
    } catch (error) {
        console.error("Error initializing acronym data:", error);
        return builtinMap;
    }
}
