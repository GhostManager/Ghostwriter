import { Node, NodeViewProps } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        footnote: {
            /**
             * Insert a footnote
             * @example editor.commands.insertFootnote({ content: 'Footnote text' })
             */
            insertFootnote: (options: { content: string }) => ReturnType;
            /**
             * Update footnote content
             * @example editor.commands.updateFootnote({ content: 'Updated text' })
             */
            updateFootnote: (options: { content: string }) => ReturnType;
        };
    }
}

type FootnoteOptions = Record<string, never>;

// Simple view component for footnotes in the editor
function FootnoteView({ node, getPos, editor }: NodeViewProps) {
    // Calculate footnote number by counting footnotes before this one
    let footnoteNumber = 1;
    if (typeof getPos === "function") {
        const pos = getPos();
        if (pos !== undefined) {
            editor.state.doc.nodesBetween(0, pos, (n) => {
                if (n.type.name === "footnote") {
                    footnoteNumber++;
                }
            });
        }
    }

    return (
        <NodeViewWrapper as="span" className="footnote-marker">
            <sup
                className="footnote-ref"
                title={node.attrs.content || "Empty footnote"}
                style={{ cursor: "pointer", color: "#0066cc" }}
            >
                {footnoteNumber}
            </sup>
        </NodeViewWrapper>
    );
}

const Footnote = Node.create<FootnoteOptions>({
    name: "footnote",
    group: "inline",
    inline: true,
    atom: true, // Cannot be edited directly, must use commands

    addAttributes() {
        return {
            content: {
                default: "",
                parseHTML: (el) => el.textContent || "",
                renderHTML: () => ({}), // Content goes inside the element
            },
        };
    },

    parseHTML() {
        return [
            {
                tag: "span.footnote",
            },
        ];
    },

    renderHTML({ node }) {
        return ["span", { class: "footnote" }, node.attrs.content];
    },

    renderText({ node }) {
        return `[^${node.attrs.content}]`;
    },

    addNodeView() {
        return ReactNodeViewRenderer(FootnoteView);
    },

    addCommands() {
        return {
            insertFootnote:
                (options) =>
                ({ commands }) => {
                    return commands.insertContent({
                        type: this.name,
                        attrs: { content: options.content },
                    });
                },
            updateFootnote:
                (options) =>
                ({ commands }) => {
                    return commands.updateAttributes(this.name, {
                        content: options.content,
                    });
                },
        };
    },
});

export default Footnote;
