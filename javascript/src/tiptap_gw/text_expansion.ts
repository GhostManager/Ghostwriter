import { Extension } from "@tiptap/core";
import type { EditorState } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { initializeAcronymData } from "./acronym_api";

export interface AcronymExpansion {
    full: string;
}

export type AcronymMap = Record<string, AcronymExpansion[]>;

// Import builtin acronym data as fallback
// Note: This will be loaded as a static asset during build
import acronymDataRaw from "../data/acronyms.yml";

// Cast the imported data to the expected type
const builtinAcronymData = acronymDataRaw as AcronymMap;

// This will be populated with merged database + builtin acronyms
let acronymData: AcronymMap = builtinAcronymData;

// Initialize acronym data from API on module load
initializeAcronymData(builtinAcronymData).then((mergedData) => {
    acronymData = mergedData;
});

// Plugin key for managing decorations
const textExpansionPluginKey = new PluginKey("textExpansion");

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        textExpansion: {
            /**
             * Expand single-definition acronyms and highlight multi-definition ones
             * @example editor.commands.expandAcronym()
             */
            expandAcronym: () => ReturnType;
            /**
             * Clear all text expansion highlights
             * @example editor.commands.clearExpansionHighlights()
             */
            clearExpansionHighlights: () => ReturnType;
        };
    }

    // Declare custom editor events
    interface EditorEvents {
        showExpansionModal: {
            word: string;
            matches: AcronymExpansion[];
            from: number;
            to: number;
        };
    }
}

/**
 * Extract all acronyms from the document.
 * Acronym criteria: 3+ letters, all uppercase (A-Z)
 */
export function extractAllAcronyms(state: EditorState): Array<{
    word: string;
    from: number;
    to: number;
}> {
    const acronyms: Array<{ word: string; from: number; to: number }> = [];
    const { doc } = state;

    // Traverse the entire document
    doc.descendants((node, pos) => {
        if (node.isText && node.text) {
            // Match 3+ letter all-caps words (only A-Z)
            const regex = /\b([A-Z]{3,})\b/g;
            let match;

            while ((match = regex.exec(node.text)) !== null) {
                acronyms.push({
                    word: match[1],
                    from: pos + match.index,
                    to: pos + match.index + match[1].length,
                });
            }
        }
        return true; // Continue traversing
    });

    return acronyms;
}

/**
 * Find acronym expansions for a given word.
 * Returns array of expansions or empty array if not found.
 */
export function findAcronymExpansions(
    word: string,
    map: AcronymMap
): AcronymExpansion[] {
    // Exact case-sensitive lookup (acronyms are uppercase)
    return map[word] || [];
}

const TextExpansion = Extension.create({
    name: "textExpansion",

    addKeyboardShortcuts() {
        return {
            // Ctrl+E on Windows/Linux, Cmd+E on Mac
            "Mod-e": () => this.editor.commands.expandAcronym(),
        };
    },

    addCommands() {
        return {
            expandAcronym:
                () =>
                ({ state, tr, dispatch, editor }) => {
                    // Extract all acronyms (3+ letters, all caps)
                    const acronyms = extractAllAcronyms(state);

                    if (acronyms.length === 0) {
                        return false; // No acronyms found
                    }

                    let replacementsMade = 0;
                    const decorations: Decoration[] = [];

                    // Process acronyms from end to start to maintain correct positions
                    const sortedAcronyms = [...acronyms].sort(
                        (a, b) => b.from - a.from
                    );

                    for (const { word, from, to } of sortedAcronyms) {
                        const expansions = findAcronymExpansions(
                            word,
                            acronymData
                        );

                        if (expansions.length === 1) {
                            // Single definition: auto-expand
                            tr.insertText(expansions[0].full, from, to);
                            replacementsMade++;
                        } else if (expansions.length > 1) {
                            // Multiple definitions: add highlight decoration
                            const decoration = Decoration.inline(from, to, {
                                class: "acronym-multi-definition",
                                "data-word": word,
                                "data-from": String(from),
                                "data-to": String(to),
                            });
                            decorations.push(decoration);
                        }
                    }

                    // Store decorations in plugin state
                    if (decorations.length > 0) {
                        tr.setMeta(textExpansionPluginKey, { decorations });
                    }

                    if (replacementsMade > 0 || decorations.length > 0) {
                        if (dispatch) {
                            dispatch(tr);
                        }
                        return true;
                    }

                    return false;
                },
            clearExpansionHighlights:
                () =>
                ({ tr, dispatch }) => {
                    // Clear all decorations by setting empty array
                    tr.setMeta(textExpansionPluginKey, { decorations: [] });

                    if (dispatch) {
                        dispatch(tr);
                    }
                    return true;
                },
        };
    },

    addProseMirrorPlugins() {
        const editor = this.editor;

        return [
            new Plugin({
                key: textExpansionPluginKey,
                state: {
                    init() {
                        return DecorationSet.empty;
                    },
                    apply(tr, decorationSet) {
                        // Update decorations based on document changes
                        decorationSet = decorationSet.map(tr.mapping, tr.doc);

                        // Add new decorations from command
                        const meta = tr.getMeta(textExpansionPluginKey);
                        if (meta?.decorations) {
                            decorationSet = DecorationSet.create(
                                tr.doc,
                                meta.decorations
                            );
                        }

                        return decorationSet;
                    },
                },
                props: {
                    decorations(state) {
                        return this.getState(state);
                    },
                    handleClick(view, pos, event) {
                        const target = event.target as HTMLElement;

                        if (
                            target.classList.contains(
                                "acronym-multi-definition"
                            )
                        ) {
                            const word = target.getAttribute("data-word");
                            const fromStr = target.getAttribute("data-from");
                            const toStr = target.getAttribute("data-to");

                            if (!word || !fromStr || !toStr) return false;

                            const from = parseInt(fromStr, 10);
                            const to = parseInt(toStr, 10);

                            const expansions = findAcronymExpansions(
                                word,
                                acronymData
                            );
                            if (expansions.length === 0) return false;

                            // Emit event with correct from/to positions
                            editor.emit("showExpansionModal", {
                                word,
                                matches: expansions,
                                from,
                                to,
                            });

                            return true; // Prevent default behavior
                        }

                        return false;
                    },
                },
            }),
        ];
    },
});

export default TextExpansion;
