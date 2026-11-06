// Ghostwriter extensions to the Tiptap tables

import { Attributes, mergeAttributes, Node } from "@tiptap/core";
import { Fragment, ResolvedPos, Slice } from "@tiptap/pm/model";
import { ReplaceAroundStep } from "@tiptap/pm/transform";
import {
    Table,
    TableCell,
    TableHeader,
    TableRow,
} from "@tiptap/extension-table";

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
                    node = node.cloneNode(true) as HTMLElement;
                    const caption = node.getElementsByTagName("caption")[0];
                    caption.remove();

                    const container = node.ownerDocument.createElement("div");
                    container.appendChild(node);

                    const captionP = node.ownerDocument.createElement("p");
                    captionP.classList.add("collab-table-caption");
                    container.appendChild(captionP);

                    const captionSpan =
                        node.ownerDocument.createElement("span");
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

const SAFE_CLASS_TOKEN = /^[A-Za-z_][A-Za-z0-9_-]*$/;

function sanitizeClassList(value: unknown): string | undefined {
    if (typeof value !== "string") return undefined;
    const classes = value
        .split(/\s+/)
        .filter((token) => SAFE_CLASS_TOKEN.test(token));
    return classes.length ? classes.join(" ") : undefined;
}

function sanitizeTableStyle(value: unknown): string | undefined {
    if (typeof value !== "string") return undefined;
    const allowedProperties = new Set([
        "border-collapse",
        "border-style",
        "border-width",
        "table-layout",
        "width",
    ]);
    const safeDeclarations = value
        .split(";")
        .map((declaration) => declaration.trim())
        .filter(Boolean)
        .flatMap((declaration) => {
            const separator = declaration.indexOf(":");
            if (separator < 1) return [];
            const property = declaration
                .slice(0, separator)
                .trim()
                .toLowerCase();
            const propertyValue = declaration.slice(separator + 1).trim();
            if (
                !allowedProperties.has(property) ||
                !/^[A-Za-z0-9 .,%()-]+$/.test(propertyValue)
            ) {
                return [];
            }
            return [`${property}: ${propertyValue}`];
        });
    return safeDeclarations.length ? safeDeclarations.join("; ") : undefined;
}

function sanitizeCellColor(value: unknown): string | undefined {
    if (typeof value !== "string") return undefined;
    const trimmed = value.trim();
    return /^(?:#(?:[0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})|rgba?\(\s*[\d.%\s,]+\)|[a-z]+)$/i.test(
        trimmed
    )
        ? trimmed
        : undefined;
}

export const GwTable = Table.extend({
    addAttributes() {
        return {
            class: {
                default: "table table-sm table-striped table-bordered",
                parseHTML: (element) =>
                    sanitizeClassList(element.getAttribute("class")) ||
                    "table table-sm table-striped table-bordered",
            },
            style: {
                default:
                    "border-collapse: collapse; width: 100%; border-style: solid; border-width: 1px",
                parseHTML: (element) =>
                    sanitizeTableStyle(element.getAttribute("style")) ||
                    "border-collapse: collapse; width: 100%; border-style: solid; border-width: 1px",
            },
        };
    },
});

export const GwTableRow = TableRow.extend({
    addAttributes() {
        return {
            class: {
                default: undefined,
                parseHTML: (element) =>
                    sanitizeClassList(element.getAttribute("class")),
            },
        };
    },
});

function addLegacyTableCellAttributes(attrs: Attributes): Attributes {
    attrs["class"] = {
        default: undefined,
        parseHTML: (element) =>
            sanitizeClassList(element.getAttribute("class")),
    };
    attrs["bgColor"] = {
        default: undefined,
        parseHTML: (element) =>
            sanitizeCellColor(
                element.getAttribute("data-bg-color") ||
                    element.style.backgroundColor
            ),
        renderHTML: (attributes) => {
            const bgColor = sanitizeCellColor(attributes.bgColor);
            if (!bgColor) return {};
            return {
                style: `background-color: ${bgColor}`,
                "data-bg-color": bgColor,
            };
        },
    };
    return attrs;
}

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
        return addLegacyTableCellAttributes(attrs);
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

export const GwTableHeader = TableHeader.extend({
    addAttributes() {
        const attrs: Attributes = TableHeader.config.addAttributes!.call(this);
        return addLegacyTableCellAttributes(attrs);
    },
});
