import { Extension } from "@tiptap/core";
import type { EditorState } from "@tiptap/pm/state";

export interface AcronymExpansion {
    full: string;
    category?: string;
}

export type AcronymMap = Record<string, AcronymExpansion[]>;

// Import acronym data
// Note: This will be loaded as a static asset during build
// Path goes from javascript/src/tiptap_gw/ -> repo root -> ghostwriter/modules/acronyms/
import acronymDataRaw from "../../../ghostwriter/modules/acronyms/acronyms.yml";

// Cast the imported data to the expected type
const acronymData = acronymDataRaw as AcronymMap;

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        textExpansion: {
            /**
             * Expand acronym at cursor position
             * @example editor.commands.expandAcronym()
             */
            expandAcronym: () => ReturnType;
        };
    }

    // Declare custom editor events
    interface EditorEvents {
        showExpansionModal: {
            word: string;
            matches: AcronymExpansion[];
        };
    }
}

/**
 * Extract the word before the cursor position.
 * Looks back up to 50 characters for a word boundary.
 */
export function extractWordBeforeCursor(state: EditorState): string | null {
    const { $from } = state.selection;
    
    if (!$from.parent.isTextblock) {
        return null;
    }

    const textBefore = $from.parent.textBetween(
        Math.max(0, $from.parentOffset - 50), // Look back max 50 chars
        $from.parentOffset,
        null,
        "\ufffc"
    );

    // Match word boundary (letters, numbers, underscores)
    // Prioritize uppercase sequences for acronyms
    const match = textBefore.match(/(\w+)$/);
    return match ? match[1] : null;
}

/**
 * Find acronym expansions for a given word (case-insensitive).
 */
export function findAcronym(
    word: string,
    map: AcronymMap
): AcronymExpansion[] {
    // Case-insensitive lookup
    const key = Object.keys(map).find(
        (k) => k.toLowerCase() === word.toLowerCase()
    );
    return key ? map[key] : [];
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
                ({ state, tr, dispatch }) => {
                    const word = extractWordBeforeCursor(state);
                    if (!word) {
                        return false;
                    }

                    const matches = findAcronym(word, acronymData);
                    if (matches.length === 0) {
                        return false;
                    }

                    if (matches.length === 1) {
                        // Single match: direct replacement
                        const { $from } = state.selection;
                        const from = $from.pos - word.length;
                        const to = $from.pos;

                        if (dispatch) {
                            tr.insertText(matches[0].full, from, to);
                            dispatch(tr);
                        }
                        return true;
                    }

                    // Multiple matches: trigger modal via custom event
                    // This will be caught by the React component
                    this.editor.emit("showExpansionModal", { word, matches });
                    return true;
                },
        };
    },
});

export default TextExpansion;
