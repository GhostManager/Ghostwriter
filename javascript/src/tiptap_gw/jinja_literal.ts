import { mergeAttributes, Node } from "@tiptap/core";

const ENCODED_REFERENCE_ATTRIBUTE = "data-gw-ref-encoded";

function encodeReference(ref: string): string {
    return Array.from(ref)
        .map((character) => character.codePointAt(0)!.toString(16))
        .join("-");
}

function decodeReference(encodedRef: string): string | null {
    if (!/^(?:[0-9a-f]+(?:-[0-9a-f]+)*)?$/i.test(encodedRef)) {
        return null;
    }
    try {
        return encodedRef
            .split("-")
            .filter(Boolean)
            .map((codePoint) => String.fromCodePoint(parseInt(codePoint, 16)))
            .join("");
    } catch {
        return null;
    }
}

function referenceFromElement(element: HTMLElement): string {
    const legacyRef = element.getAttribute("data-gw-ref");
    const encodedRef = element.getAttribute(ENCODED_REFERENCE_ATTRIBUTE);
    if (encodedRef !== null) {
        const decodedRef = decodeReference(encodedRef);
        if (decodedRef) {
            return decodedRef;
        }
        if (legacyRef === null) {
            return decodedRef ?? "";
        }
    }
    return legacyRef ?? "";
}

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
 * The serialized attribute contains only hexadecimal code points. The visible
 * legacy syntax is supplied by a node view and never becomes template source.
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
                parseHTML: referenceFromElement,
                renderHTML: (attributes) => ({
                    [ENCODED_REFERENCE_ATTRIBUTE]: encodeReference(
                        String(attributes.ref)
                    ),
                }),
            },
        };
    },

    parseHTML() {
        return [
            { tag: `span[${ENCODED_REFERENCE_ATTRIBUTE}]` },
            { tag: "span[data-gw-ref]" },
        ];
    },

    renderText({ node }) {
        return String(node.attrs.ref);
    },

    renderHTML({ HTMLAttributes }) {
        return ["span", HTMLAttributes];
    },

    addNodeView() {
        return ({ node }) => {
            const dom = document.createElement("span");
            dom.contentEditable = "false";
            dom.textContent = `{{.ref ${node.attrs.ref}}}`;
            return { dom };
        };
    },
});

export default JinjaLiteral;
