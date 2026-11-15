import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import React, { useState } from "react";
import EvidenceNode, {
    Evidence,
    EvidencesContext,
} from "../../src/tiptap_gw/evidence";
import { loadLatestEvidenceImage } from "../../src/frontend/graphql/evidence";

/** Real evidence node with controllable network metadata, download, and save paths. */
export function FreshOpenFixture() {
    const [evidence, setEvidence] = useState<Evidence[]>([
        {
            id: 1,
            friendlyName: "Existing evidence",
            caption: "Existing caption",
            document: "old.png",
        },
    ]);
    const [visible, setVisible] = useState(true);
    const editor = useEditor({
        extensions: [StarterKit, EvidenceNode],
        content: '<div class="richtext-evidence" data-evidence-id="1"></div>',
    });
    return (
        <>
            <button onClick={() => setVisible(false)}>
                Remove evidence view
            </button>
            <EvidencesContext.Provider
                value={{
                    evidence,
                    uploadUrl: "/test-upload",
                    poll: async () => {},
                    getLatestImage: (id) =>
                        loadLatestEvidenceImage(id, async () => {
                            const response = await fetch(
                                "/test-latest-evidence"
                            );
                            if (!response.ok)
                                throw new Error("Could not refresh evidence.");
                            const rows: Evidence[] = await response.json();
                            setEvidence(rows);
                            return rows;
                        }),
                    replaceImage: async (id, image, expected) => {
                        const body = new FormData();
                        body.append("document", image, "edited.png");
                        body.append("expected_document", expected);
                        const response = await fetch(
                            `/test-replace-image/${id}`,
                            {
                                method: "POST",
                                body,
                            }
                        );
                        if (!response.ok) throw new Error("Save rejected.");
                    },
                }}
            >
                {visible && <EditorContent editor={editor} />}
            </EvidencesContext.Provider>
        </>
    );
}
