import { Extension } from "@tiptap/core";

// TODO: title case
export type CaseType = "lower" | "upper";

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        caseChange: {
            changeCase: (newCase: CaseType) => ReturnType;
        };
    }
}

const CaseChange = Extension.create({
    name: "caseChange",
    addCommands() {
        return {
            changeCase:
                (newCase: CaseType) =>
                ({ state, tr }) => {
                    const inserts: [string, number, number][] = [];
                    // Find ranges to replace, preserving marks and nodes
                    for (const range of state.selection.ranges) {
                        state.doc.nodesBetween(
                            range.$from.pos,
                            range.$to.pos,
                            (node, pos) => {
                                if (!node.type.isText) {
                                    return true;
                                }
                                let oldText = node.text!;
                                let replaceFrom = pos;
                                let replaceTo = pos + node.nodeSize;
                                if (range.$to.pos <= replaceTo) {
                                    // Trim to selection end
                                    oldText = oldText.slice(
                                        0,
                                        range.$to.pos - pos
                                    );
                                    replaceTo = range.$to.pos;
                                }
                                if (replaceFrom < range.$from.pos) {
                                    // Trim to selection start
                                    oldText = oldText.slice(
                                        range.$from.pos - replaceFrom
                                    );
                                    replaceFrom = range.$from.pos;
                                }
                                if (oldText)
                                    inserts.push([
                                        oldText,
                                        replaceFrom,
                                        replaceTo,
                                    ]);
                                return false;
                            }
                        );
                    }

                    if (inserts.length === 0) {
                        return false;
                    }

                    for (const [oldText, from, to] of inserts) {
                        let newText;
                        if (newCase === "lower") {
                            newText = oldText.toLocaleLowerCase();
                        } else if (newCase === "upper") {
                            newText = oldText.toLocaleUpperCase();
                        } else {
                            newCase satisfies never;
                            throw new Error(
                                "Unrecognized case type: " + newCase
                            );
                        }
                        tr.insertText(
                            newText,
                            tr.mapping.map(from),
                            tr.mapping.map(to)
                        );
                    }
                    return true;
                },
        };
    },
});
export default CaseChange;
