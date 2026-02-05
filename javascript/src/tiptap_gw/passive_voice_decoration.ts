import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { type DocumentPositionRange } from "./text_position_mapper";

/**
 * Plugin key for passive voice decorations
 */
export const passiveVoicePluginKey = new PluginKey("passiveVoice");

/**
 * TipTap extension for highlighting passive voice using decorations.
 * Unlike marks, decorations are visual-only and don't affect the document data.
 * They won't be saved to the database or exported to reports.
 *
 * This extension accepts pre-converted document positions (not text offsets).
 * The caller is responsible for converting text offsets to document positions
 * using extractTextWithPositions() + convertRangesWithMap() from text_position_mapper.
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
                        // Check if we have new passive voice ranges to apply
                        const meta = tr.getMeta(passiveVoicePluginKey);
                        if (meta !== undefined) {
                            const docRanges = meta as DocumentPositionRange[];

                            if (docRanges.length === 0) {
                                // Clear all decorations
                                return DecorationSet.empty;
                            }

                            // Create decorations from pre-converted document positions
                            const decorations = docRanges.map(
                                ({ from, to }, index: number) => {
                                    const groupId = `pv-${index}`;

                                    return Decoration.inline(from, to, {
                                        class: "passive-voice-highlight",
                                        "data-passive-group": groupId,
                                    });
                                }
                            );

                            return DecorationSet.create(tr.doc, decorations);
                        }

                        // Handle document changes - remove decorations that were edited
                        if (tr.docChanged) {
                            // Get all current decorations before the change
                            const currentDecos = decorationSet.find();

                            // Find which ranges were affected by this transaction
                            const editedRanges: Array<{ from: number; to: number }> = [];
                            tr.steps.forEach((step) => {
                                const stepMap = step.getMap();
                                stepMap.forEach((oldStart, oldEnd) => {
                                    editedRanges.push({ from: oldStart, to: oldEnd });
                                });
                            });

                            // Filter: keep decorations that weren't touched by any edit
                            const survivingDecos: Decoration[] = [];

                            for (const deco of currentDecos) {
                                // Check if this decoration overlaps with any edit
                                const wasEdited = editedRanges.some(
                                    (edit) => deco.from < edit.to && deco.to > edit.from
                                );

                                if (wasEdited) {
                                    // This decoration was edited - remove it
                                    continue;
                                }

                                // Map the decoration through the transaction
                                const mappedFrom = tr.mapping.map(deco.from);
                                const mappedTo = tr.mapping.map(deco.to);

                                // Skip if it became zero-width
                                if (mappedFrom >= mappedTo) continue;

                                // Recreate with mapped positions
                                survivingDecos.push(
                                    Decoration.inline(mappedFrom, mappedTo, {
                                        class: "passive-voice-highlight",
                                        "data-passive-group": (deco as any).type?.attrs?.["data-passive-group"] || "",
                                    })
                                );
                            }

                            return DecorationSet.create(tr.doc, survivingDecos);
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
                            if (
                                target.classList &&
                                target.classList.contains(
                                    "passive-voice-highlight"
                                )
                            ) {
                                const groupId =
                                    target.getAttribute("data-passive-group");
                                if (groupId && groupId !== hoverGroupId) {
                                    hoverGroupId = groupId;
                                    // Add hover class to all segments in this group
                                    const elements = view.dom.querySelectorAll(
                                        `.passive-voice-highlight[data-passive-group="${groupId}"]`
                                    );
                                    elements.forEach((el) =>
                                        el.classList.add("passive-voice-hover")
                                    );
                                }
                            }
                        },
                        mouseout(view, event) {
                            const target = event.target as HTMLElement;
                            const relatedTarget =
                                event.relatedTarget as HTMLElement;

                            // Only clear if we're leaving the group entirely
                            if (
                                target.classList &&
                                target.classList.contains(
                                    "passive-voice-highlight"
                                )
                            ) {
                                const groupId =
                                    target.getAttribute("data-passive-group");

                                // Check if we're moving to another element in same group
                                if (
                                    !relatedTarget ||
                                    !relatedTarget.classList ||
                                    !relatedTarget.classList.contains(
                                        "passive-voice-highlight"
                                    ) ||
                                    relatedTarget.getAttribute(
                                        "data-passive-group"
                                    ) !== groupId
                                ) {
                                    hoverGroupId = null;
                                    // Remove hover class from all segments
                                    view.dom
                                        .querySelectorAll(
                                            ".passive-voice-hover"
                                        )
                                        .forEach((el) =>
                                            el.classList.remove(
                                                "passive-voice-hover"
                                            )
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
             * Set passive voice ranges to highlight (using document positions)
             */
            setPassiveVoiceDocRanges:
                (ranges: DocumentPositionRange[]) =>
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
             * Set passive voice ranges to highlight (using document positions)
             */
            setPassiveVoiceDocRanges: (
                ranges: DocumentPositionRange[]
            ) => ReturnType;
            /**
             * Clear all passive voice highlights
             */
            clearPassiveVoice: () => ReturnType;
        };
    }
}
