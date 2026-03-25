import { mergeAttributes, Node, NodeViewProps } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import React, { useContext, useState } from "react";
import ReactModal from "react-modal";

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
                this.editor.view.dom.dispatchEvent(
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
    uploadUrl: string;
    poll: () => Promise<void>;
};

export const EvidencesContext = React.createContext<Evidences | null>(null);

const TEXT_EXTENSIONS = [".txt", ".log", ".md"];
const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg"];

// Custom hook to fetch text content of an evidence if it's a text file
function useTextContent(id: number, isText: boolean): string | null {
    const [content, setContent] = React.useState<string | null>(null);
    React.useEffect(() => {
        if (!isText) return;
        fetch("/reporting/evidence/download/" + id)
            .then((r) => {
                if (!r.ok) throw new Error(r.statusText);
                return r.text();
            })
            .then(setContent)
            .catch(() => setContent(null));
    }, [id, isText]);
    return content;
}

function EvidenceView(props: NodeViewProps) {
    const id = parseInt(props.node.attrs.id);
    const ghostwriterEvidences = useContext(EvidencesContext);
    const evidence =
        ghostwriterEvidences &&
        ghostwriterEvidences.evidence.find((v) => v.id === id);

    const [lightboxOpen, setLightboxOpen] = useState(false);

    const isImage =
        !!evidence &&
        IMAGE_EXTENSIONS.some((ext) => evidence.document.endsWith(ext));
    const isText =
        !!evidence &&
        TEXT_EXTENSIONS.some((ext) => evidence.document.endsWith(ext));
    const textContent = useTextContent(id, isText);

    if (!evidence) {
        return (
            <NodeViewWrapper className="richtext-evidence">
                <span className="richtext-evidence-missing">
                    (Evidence Missing)
                </span>
            </NodeViewWrapper>
        );
    }

    let preview = null;
    if (isImage) {
        const url = "/reporting/evidence/download/" + evidence.id;
        preview = (
            <>
                <img src={url} onClick={() => setLightboxOpen(true)} />
                <ReactModal
                    isOpen={lightboxOpen}
                    onRequestClose={() => setLightboxOpen(false)}
                    contentLabel="Lightbox"
                    className="rich-text-lightbox"
                >
                    <img src={url} />
                </ReactModal>
            </>
        );
    } else if (isText) {
        preview = (
            <pre className="richtext-evidence-text">
                <code>
                    {textContent === null ? "Loading…" : textContent}
                </code>
            </pre>
        );
    }

    return (
        <NodeViewWrapper className="richtext-evidence">
            <span className="richtext-evidence-name">
                {evidence.friendlyName}
            </span>
            {preview}
            <span className="richtext-evidence-caption">
                {"Evidence: " + evidence.caption}
            </span>
        </NodeViewWrapper>
    );
}

export default Evidence;
