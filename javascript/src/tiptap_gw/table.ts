// Ghostwriter extensions to the Tiptap tables

import { Attributes, mergeAttributes, Node } from "@tiptap/core";
import { Fragment, ResolvedPos, Slice } from "@tiptap/pm/model";
import { ReplaceAroundStep } from "@tiptap/pm/transform";
import TableCell from "@tiptap/extension-table-cell";
import mkElem from "./mkelem";

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        tableCaption: {
            addCaption: () => ReturnType;
            removeCaption: () => ReturnType;
            setTableCaptionBookmark: (name: string | undefined) => ReturnType;
        };
        tableCell: {
            setTableCellBackgroundColor: (color: string | null) => ReturnType;
        };
    }
}

// Wrapper for table that includes a caption
export const TableWithCaption = Node.create<{}>({
    name: "tableWithCaption",
    group: "block",
    content: "table tableCaption",
    isolating: true,
    // Parse before regular table
    priority: 101,

    parseHTML() {
        return [
            {
                tag: "div",
                getAttrs: (node) =>
                    node.classList.contains("collab-table-wrapper") && null,
            },
            {
                // Hacky way to convert a table with a caption element to this wrapped format.
                tag: "table",
                getAttrs: (node) => {
                    // Check if there is a caption, otherwise let the normal table element do it
                    if (node.getElementsByTagName("caption").length > 0) {
                        return null;
                    }
                    return false;
                },
                contentElement: (node) => {
                    // Convert to wrapped format
                    node = node.cloneNode(true);
                    const caption = (node as HTMLElement).getElementsByTagName(
                        "caption"
                    )[0];
                    caption.remove();

                    const container = mkElem("div");
                    container.appendChild(node);

                    const captionP = mkElem("p");
                    captionP.classList.add("collab-table-caption");
                    container.appendChild(captionP);

                    const captionSpan = mkElem("span");
                    captionSpan.classList.add("collab-table-caption-content");
                    for (const node of Array.from(caption.childNodes)) {
                        captionSpan.appendChild(node);
                    }
                    captionP.appendChild(captionSpan);

                    return container;
                },
            },
        ];
    },
    renderHTML() {
        return ["div", { class: "collab-table-wrapper" }, 0];
    },
    renderText() {
        return "";
    },
});

function findParent($pos: ResolvedPos, name: string): ResolvedPos | null {
    for (let d = $pos.depth - 1; d > 0; d--)
        if ($pos.node(d).type.name === name)
            return $pos.node(0).resolve($pos.before(d + 1));
    return null;
}

export const TableCaption = Node.create<{}>({
    name: "tableCaption",
    content: "inline*",
    // Parse before regular p
    priority: 1001,

    addAttributes() {
        return {
            bookmark: {
                default: undefined,
                parseHTML: (el) =>
                    el.getAttribute("data-bookmark") || undefined,
                renderHTML: (attr) => ({
                    "data-bookmark": attr.bookmark || undefined,
                }),
            },
        };
    },

    parseHTML() {
        return [
            {
                tag: "p",
                getAttrs: (node) =>
                    node.classList.contains("collab-table-caption") && null,
                contentElement: ".collab-table-caption-content",
            },
        ];
    },

    renderHTML({ HTMLAttributes }) {
        return [
            "p",
            mergeAttributes(HTMLAttributes, { class: "collab-table-caption" }),
            [
                "span",
                {
                    class: "collab-table-caption-prefix",
                    contenteditable: "false",
                },
                "Table #:",
            ],
            ["span", { class: "collab-table-caption-content" }, 0],
        ];
    },

    addCommands() {
        return {
            addCaption:
                () =>
                ({ state, dispatch }) => {
                    let $pos = findParent(state.selection.$head, "table");
                    if (!$pos) return false;
                    if (
                        $pos.depth >= 2 &&
                        $pos.node(-1).type.name === "tableWithCaption"
                    )
                        return false;
                    if (dispatch) {
                        const tr = state.tr;
                        const start = $pos.before();
                        const end = $pos.after();
                        const fragment = Fragment.from(
                            state.schema.nodes["tableWithCaption"].create(
                                null,
                                Fragment.from(
                                    state.schema.nodes["tableCaption"].create(
                                        null,
                                        Fragment.from(
                                            state.schema.text("Caption")
                                        )
                                    )
                                )
                            )
                        );
                        tr.step(
                            new ReplaceAroundStep(
                                start,
                                end,
                                start,
                                end,
                                new Slice(fragment, 0, 0),
                                1
                            )
                        );
                        dispatch(tr);
                    }
                    return true;
                },
            removeCaption:
                () =>
                ({ state, dispatch }) => {
                    let $pos = findParent(
                        state.selection.$head,
                        "tableWithCaption"
                    );
                    if (!$pos) return false;
                    if (dispatch) {
                        const tr = state.tr;
                        const start = $pos.before() + 1;
                        const end = start + $pos.node().child(0).nodeSize;
                        tr.step(
                            new ReplaceAroundStep(
                                $pos.before(),
                                $pos.after(),
                                start,
                                end,
                                new Slice(Fragment.empty, 0, 0),
                                0
                            )
                        );
                        dispatch(tr);
                    }
                    return true;
                },
            setTableCaptionBookmark:
                (name) =>
                ({ commands, can }) => {
                    // Check if we're even in a heading, and don't enable this command if so.
                    if (!can().deleteNode(this.name)) return false;
                    return commands.updateAttributes(this.name, {
                        bookmark: name,
                    });
                },
        };
    },
});

export const GwTableCell = TableCell.extend({
    addAttributes() {
        const attrs: Attributes = TableCell.config.addAttributes!.call(this);
        attrs["bgColor"] = {
            default: undefined,
            parseHTML: (el) => el.getAttribute("data-bg-color"),
            renderHTML: (attributes) => {
                if (!attributes.bgColor) return {};
                return {
                    style: `background-color: ${attributes.bgColor}`,
                    "data-bg-color": attributes.bgColor,
                };
            },
        };
        return attrs;
    },
    addCommands() {
        return {
            setTableCellBackgroundColor:
                (color) =>
                ({ commands, can }) => {
                    // Check if we're even in a heading, and don't enable this command if so.
                    if (!can().deleteNode(this.name)) return false;
                    return commands.updateAttributes(this.name, {
                        bgColor: color || undefined,
                    });
                },
        };
    },
});
