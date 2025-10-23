import { Node, NodeViewProps } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        image: {
            insertGwImage: (name: string) => ReturnType;
        };
    }
}

export const IMAGE_TYPES: Map<string, string> = new Map([
    ["CLIENT_LOGO", "Client Logo"],
]);

const Image = Node.create<{}>({
    name: "gwImage",
    group: "block",
    draggable: true,

    addAttributes() {
        return {
            imgName: {
                default: null,
                parseHTML: (el) => el.getAttribute("data-gw-image"),
                renderHTML: (attrs) => ({
                    "data-gw-image": attrs.imgName,
                }),
            },
        };
    },
    parseHTML() {
        return [
            {
                tag: "div",
                getAttrs: (node) => node.hasAttribute("data-gw-image") && null,
            },
        ];
    },
    renderText({ node }) {
        return node.attrs.imgName;
    },
    renderHTML({ HTMLAttributes }) {
        console.log("DEBUG renderHtml", HTMLAttributes);
        return ["div", HTMLAttributes];
    },
    addNodeView() {
        return ReactNodeViewRenderer(ImageView);
    },
    addCommands() {
        return {
            insertGwImage:
                (name: string) =>
                ({ commands }) => {
                    return commands.insertContent({
                        type: this.name,
                        attrs: {
                            imgName: name,
                        },
                    });
                },
        };
    },
});
export default Image;

function ImageView(props: NodeViewProps) {
    return (
        <NodeViewWrapper className="richtext-evidence">
            <span className="richtext-evidence-name">
                {IMAGE_TYPES.get(props.node.attrs.imgName) ??
                    props.node.attrs.imgName}
            </span>
        </NodeViewWrapper>
    );
}
