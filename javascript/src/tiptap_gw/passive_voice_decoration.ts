import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

export interface PassiveVoiceRange {
    start: number;
    end: number;
}

/**
 * Plugin key for passive voice decorations
 */
export const passiveVoicePluginKey = new PluginKey("passiveVoice");

/**
 * TipTap extension for highlighting passive voice using decorations.
 * Unlike marks, decorations are visual-only and don't affect the document data.
 * They won't be saved to the database or exported to reports.
 */
export const PassiveVoiceDecoration = Extension.create({
    name: "passiveVoice",

    addProseMirrorPlugins() {
        let hoverGroupId: string | null = null;

        return [
            new Plugin({
                key: passiveVoicePluginKey,
                state: {
                    init() {
                        return DecorationSet.empty;
                    },
                    apply(tr, decorationSet) {
                        // Map decorations through document changes
                        decorationSet = decorationSet.map(tr.mapping, tr.doc);

                        // Check if we have new passive voice ranges to apply
                        const ranges = tr.getMeta(passiveVoicePluginKey);
                        if (ranges) {
                            if (ranges.length === 0) {
                                // Clear all decorations
                                return DecorationSet.empty;
                            }

                            // Create new decoration set with unique group IDs for each range
                            const decorations = ranges.flatMap(
                                ({ start, end }: PassiveVoiceRange, index: number) => {
                                    // TipTap uses 1-based indexing, server uses 0-based
                                    const from = start + 1;
                                    const to = end + 1;
                                    const groupId = `pv-${index}`;

                                    return Decoration.inline(from, to, {
                                        class: "passive-voice-highlight",
                                        nodeName: "mark",
                                        "data-passive-group": groupId,
                                    });
                                }
                            );

                            return DecorationSet.create(tr.doc, decorations);
                        }

                        return decorationSet;
                    },
                },
                props: {
                    decorations(state) {
                        return this.getState(state);
                    },
                    handleDOMEvents: {
                        mouseover(view, event) {
                            const target = event.target as HTMLElement;
                            if (target.classList && target.classList.contains("passive-voice-highlight")) {
                                const groupId = target.getAttribute("data-passive-group");
                                if (groupId && groupId !== hoverGroupId) {
                                    hoverGroupId = groupId;
                                    // Add hover class to all segments in this group
                                    const elements = view.dom.querySelectorAll(
                                        `.passive-voice-highlight[data-passive-group="${groupId}"]`
                                    );
                                    elements.forEach((el) => el.classList.add("passive-voice-hover"));
                                }
                            }
                        },
                        mouseout(view, event) {
                            const target = event.target as HTMLElement;
                            const relatedTarget = event.relatedTarget as HTMLElement;

                            // Only clear if we're leaving the group entirely
                            if (target.classList && target.classList.contains("passive-voice-highlight")) {
                                const groupId = target.getAttribute("data-passive-group");

                                // Check if we're moving to another element in same group
                                if (!relatedTarget ||
                                    !relatedTarget.classList ||
                                    !relatedTarget.classList.contains("passive-voice-highlight") ||
                                    relatedTarget.getAttribute("data-passive-group") !== groupId) {

                                    hoverGroupId = null;
                                    // Remove hover class from all segments
                                    view.dom.querySelectorAll(".passive-voice-hover").forEach((el) =>
                                        el.classList.remove("passive-voice-hover")
                                    );
                                }
                            }
                        },
                    },
                },
            }),
        ];
    },

    addCommands() {
        return {
            /**
             * Set passive voice ranges to highlight
             */
            setPassiveVoiceRanges:
                (ranges: PassiveVoiceRange[]) =>
                ({ tr, dispatch }) => {
                    if (dispatch) {
                        tr.setMeta(passiveVoicePluginKey, ranges);
                        dispatch(tr);
                    }
                    return true;
                },

            /**
             * Clear all passive voice highlights
             */
            clearPassiveVoice:
                () =>
                ({ tr, dispatch }) => {
                    if (dispatch) {
                        tr.setMeta(passiveVoicePluginKey, []);
                        dispatch(tr);
                    }
                    return true;
                },
        };
    },
});

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        passiveVoice: {
            /**
             * Set passive voice ranges to highlight
             */
            setPassiveVoiceRanges: (ranges: PassiveVoiceRange[]) => ReturnType;
            /**
             * Clear all passive voice highlights
             */
            clearPassiveVoice: () => ReturnType;
        };
    }
}
