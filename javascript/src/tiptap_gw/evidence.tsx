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
                    (node as any).classList.contains("richtext-evidence") &&
                    null,
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

    if (
        evidence.document.endsWith(".png") ||
        evidence.document.endsWith(".jpg") ||
        evidence.document.endsWith(".jpeg")
    ) {
        return (
            <NodeViewWrapper className="richtext-evidence">
                <img
                    src={ghostwriterEvidences.mediaUrl + evidence["document"]}
                />
                <span className="richtext-evidence-name">
                    {"Evidence: " + evidence.friendlyName}
                </span>
            </NodeViewWrapper>
        );
    }

    return (
        <NodeViewWrapper className="richtext-evidence">
            <span className="richtext-evidence-name">
                {"Evidence: " + evidence.friendlyName}
            </span>
        </NodeViewWrapper>
    );
}

export default Evidence;
