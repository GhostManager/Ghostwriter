import { mergeAttributes, Node } from "@tiptap/core";

/**
 * Marks generated report content as literal data.
 *
 * The report renderer removes this wrapper before compiling the surrounding
 * rich text as Jinja and restores its contents after rendering.
 */
const JinjaLiteral = Node.create({
    name: "jinjaLiteral",
    group: "block",
    content: "block+",
    defining: true,

    parseHTML() {
        return [{ tag: "div[data-gw-jinja-literal]" }];
    },

    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, {
                "data-gw-jinja-literal": "true",
            }),
            0,
        ];
    },
});

/**
 * A structured cross-reference used by generated oplog outlines.
 *
 * Keeping the reference name in a node attribute avoids constructing legacy
 * `{{.ref ...}}` template source from an evidence friendly name.
 */
export const JinjaReference = Node.create({
    name: "jinjaReference",
    group: "inline",
    inline: true,
    atom: true,

    addAttributes() {
        return {
            ref: {
                default: "",
                parseHTML: (element) =>
                    element.getAttribute("data-gw-ref") ?? "",
                renderHTML: (attributes) => ({
                    "data-gw-ref": attributes.ref,
                }),
            },
        };
    },

    parseHTML() {
        return [{ tag: "span[data-gw-ref]" }];
    },

    renderText({ node }) {
        return `{{.ref ${node.attrs.ref}}}`;
    },

    renderHTML({ node, HTMLAttributes }) {
        return ["span", HTMLAttributes, `{{.ref ${node.attrs.ref}}}`];
    },
});

export default JinjaLiteral;
