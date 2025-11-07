import { isNodeSelection, mergeAttributes, Node } from "@tiptap/core";
import { NodeSelection, TextSelection } from "@tiptap/pm/state";

// Based off of the horizontal rule:
// https://github.com/ueberdosis/tiptap/blob/main/packages/extension-horizontal-rule/src/horizontal-rule.ts

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        setPageBreak: {
            /**
             * Add a page break
             * @example editor.commands.setPageBreak()
             */
            setPageBreak: () => ReturnType;
        };
    }
}

type PageBreakOptions = {};
const PageBreak = Node.create<PageBreakOptions>({
    name: "pageBreak",
    group: "block",
    priority: 101, // before regular <br/>
    parseHTML() {
        return [
            {
                tag: "div",
                getAttrs: (node) =>
                    node.classList.contains("page-break") && null,
            },
            {
                tag: "br",
                getAttrs: (node) =>
                    node.hasAttribute("data-gw-pagebreak") && null,
            },
        ];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(
                { class: "page-break", contenteditable: false },
                HTMLAttributes
            ),
            ["div", { class: "page-break-line" }],
            ["div", { class: "page-break-text" }, "Page Break"],
            ["div", { class: "page-break-line" }],
        ];
    },
    renderText() {
        return "\n";
    },
    addCommands() {
        return {
            setPageBreak:
                () =>
                ({ chain, state }) => {
                    const { selection } = state;
                    const { $from: $originFrom, $to: $originTo } = selection;

                    const currentChain = chain();

                    if ($originFrom.parentOffset === 0) {
                        currentChain.insertContentAt(
                            {
                                from: Math.max($originFrom.pos - 1, 0),
                                to: $originTo.pos,
                            },
                            {
                                type: this.name,
                            }
                        );
                    } else if (isNodeSelection(selection)) {
                        currentChain.insertContentAt($originTo.pos, {
                            type: this.name,
                        });
                    } else {
                        currentChain.insertContent({ type: this.name });
                    }

                    return (
                        currentChain
                            // set cursor after horizontal rule
                            .command(({ tr, dispatch }) => {
                                if (dispatch) {
                                    const { $to } = tr.selection;
                                    const posAfter = $to.end();

                                    if ($to.nodeAfter) {
                                        if ($to.nodeAfter.isTextblock) {
                                            tr.setSelection(
                                                TextSelection.create(
                                                    tr.doc,
                                                    $to.pos + 1
                                                )
                                            );
                                        } else if ($to.nodeAfter.isBlock) {
                                            tr.setSelection(
                                                NodeSelection.create(
                                                    tr.doc,
                                                    $to.pos
                                                )
                                            );
                                        } else {
                                            tr.setSelection(
                                                TextSelection.create(
                                                    tr.doc,
                                                    $to.pos
                                                )
                                            );
                                        }
                                    } else {
                                        // add node after horizontal rule if it’s the end of the document
                                        const node =
                                            $to.parent.type.contentMatch.defaultType?.create();

                                        if (node) {
                                            tr.insert(posAfter, node);
                                            tr.setSelection(
                                                TextSelection.create(
                                                    tr.doc,
                                                    posAfter + 1
                                                )
                                            );
                                        }
                                    }

                                    tr.scrollIntoView();
                                }

                                return true;
                            })
                            .run()
                    );
                },
        };
    },
});

export default PageBreak;
