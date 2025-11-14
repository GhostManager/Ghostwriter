import { Node, NodeViewProps } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        caption: {
            setCaption: (name: string) => ReturnType;
        };
    }
}

const Caption = Node.create<{}>({
    name: "caption",
    group: "block",
    draggable: true,

    addAttributes() {
        return {
            ref: {
                default: "",
                parseHTML: (el) => el.getAttribute("data-gw-caption"),
                renderHTML: (attrs) => ({
                    "data-gw-caption": attrs.ref,
                }),
            },
        };
    },

    parseHTML() {
        return [
            {
                tag: "div",
                getAttrs: (node) =>
                    node.hasAttribute("data-gw-caption") && null,
            },
        ];
    },

    renderText() {
        return "Figure #";
    },

    renderHTML({ HTMLAttributes }) {
        return ["div", HTMLAttributes];
    },

    addNodeView() {
        return ReactNodeViewRenderer(CaptionView);
    },

    addCommands() {
        return {
            setCaption:
                (ref) =>
                ({ commands }) =>
                    commands.insertContent({
                        type: this.name,
                        attrs: { ref },
                    }),
        };
    },
});

function CaptionView(props: NodeViewProps) {
    return (
        <NodeViewWrapper className="richtext-evidence">
            <span className="richtext-evidence-caption">
                Figure #
                {props.node.attrs.ref ? (
                    <>
                        {" "}
                        (<code>{props.node.attrs.ref}</code>)
                    </>
                ) : null}
            </span>
        </NodeViewWrapper>
    );
}

export default Caption;
