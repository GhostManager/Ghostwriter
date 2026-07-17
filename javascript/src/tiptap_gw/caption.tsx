import { Node, NodeViewProps } from "@tiptap/core";
import {
    NodeViewContent,
    NodeViewWrapper,
    ReactNodeViewRenderer,
} from "@tiptap/react";

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
    content: "text*",
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
        return ["div", HTMLAttributes, 0];
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
                        content: [
                            {
                                type: "text",
                                text: "Caption",
                            },
                        ],
                    }),
        };
    },
});

function CaptionView(props: NodeViewProps) {
    return (
        <NodeViewWrapper className="richtext-evidence">
            <div className="richtext-evidence-prefix">
                Figure #
                {props.node.attrs.ref ? (
                    <>
                        {" "}
                        (<code>{props.node.attrs.ref}</code>)
                    </>
                ) : null}
                :
            </div>
            <NodeViewContent className="richtext-evidence-text-field" />
            <div className="richtext-evidence-help small text-muted">
                Enter caption text above
            </div>
        </NodeViewWrapper>
    );
}

export default Caption;
