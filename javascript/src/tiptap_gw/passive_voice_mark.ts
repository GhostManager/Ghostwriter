import { Mark } from "@tiptap/core";

/**
 * TipTap mark for highlighting passive voice text.
 * Applied using character ranges from server.
 *
 * Note: This mark is non-inclusive, meaning typing at the boundaries
 * won't extend the mark. Editing within the mark will remove it.
 */
export const PassiveVoiceMark = Mark.create({
    name: "passiveVoice",

    // Make the mark non-inclusive so it doesn't extend to new typing
    inclusive: false,

    addAttributes() {
        return {
            class: {
                default: "passive-voice-highlight",
            },
        };
    },

    parseHTML() {
        return [
            {
                tag: "mark.passive-voice-highlight",
            },
        ];
    },

    renderHTML({ HTMLAttributes }) {
        return [
            "mark",
            { ...HTMLAttributes, class: "passive-voice-highlight" },
            0,
        ];
    },
});
