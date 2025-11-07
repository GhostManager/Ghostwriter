import { mergeAttributes, Node, NodeViewProps } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import React, { useContext } from "react";

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        evidence: {
            setEvidence: (options: { id: number }) => ReturnType;
        };
    }
}

type EvidenceOptions = {};
const Evidence = Node.create<EvidenceOptions>({
    name: "evidence",
    group: "block",
    draggable: true,

    addAttributes() {
        return {
            id: {
                default: null,
                parseHTML: (el) => el.getAttribute("data-evidence-id"),
                renderHTML: (attrs) => ({
                    "data-evidence-id": attrs.id,
                }),
            },
        };
    },

    parseHTML() {
        return [
            {
                tag: "div",
                getAttrs: (node) =>
                    node.classList.contains("richtext-evidence") && null,
            },
        ];
    },

    renderText({ node }) {
        return node.attrs.name ? "Evidence " + node.attrs.name : "Evidence";
    },

    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(
                {
                    class: "richtext-evidence",
                },
                HTMLAttributes
            ),
        ];
    },

    addNodeView() {
        return ReactNodeViewRenderer(EvidenceView);
    },

    addCommands() {
        return {
            setEvidence:
                (options) =>
                ({ commands }) =>
                    commands.insertContent({
                        type: this.name,
                        attrs: options,
                    }),
        };
    },

    addKeyboardShortcuts() {
        return {
            "Mod-Shift-d": () =>
                this.editor.options.element.dispatchEvent(
                    new CustomEvent("openevidencemodal")
                ),
        };
    },
});

export type Evidence = {
    id: number;
    friendlyName: string;
    caption: string;
    document: string;
};

export type Evidences = {
    evidence: Evidence[];
    mediaUrl: string;
    uploadUrl: string;
    poll: () => Promise<void>;
};

export const EvidencesContext = React.createContext<Evidences | null>(null);

function EvidenceView(props: NodeViewProps) {
    const id = parseInt(props.node.attrs.id);
    const ghostwriterEvidences = useContext(EvidencesContext);
    const evidence =
        ghostwriterEvidences &&
        ghostwriterEvidences.evidence.find((v) => v.id === id);

    if (!evidence) {
        return (
            <NodeViewWrapper className="richtext-evidence">
                <span className="richtext-evidence-missing">
                    (Evidence Missing)
                </span>
            </NodeViewWrapper>
        );
    }

    let img = null;
    if (
        evidence.document.endsWith(".png") ||
        evidence.document.endsWith(".jpg") ||
        evidence.document.endsWith(".jpeg")
    ) {
        img = (
            <img src={ghostwriterEvidences.mediaUrl + evidence["document"]} />
        );
    }

    return (
        <NodeViewWrapper className="richtext-evidence">
            <span className="richtext-evidence-name">
                {evidence.friendlyName}
            </span>
            {img}
            <span className="richtext-evidence-caption">
                {"Evidence: " + evidence.caption}
            </span>
        </NodeViewWrapper>
    );
}

export default Evidence;
