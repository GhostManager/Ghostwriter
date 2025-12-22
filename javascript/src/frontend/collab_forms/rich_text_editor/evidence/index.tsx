import { faPaperclip } from "@fortawesome/free-solid-svg-icons/faPaperclip";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Editor } from "@tiptap/core";
import { useCallback, useEffect, useState } from "react";
import EvidenceModal from "./modal";
import { useEditorState } from "@tiptap/react";

export default function EvidenceButton({ editor }: { editor: Editor }) {
    // null = closed, "new" = inserting, number = editing with the existing ID as the number
    const [modalInitial, setModalInitial] = useState<null | "new" | number>(
        null
    );

    const { enabled, active } = useEditorState({
        editor,
        selector: ({ editor }) => {
            if (!editor.isInitialized) return { enabled: false, active: false };
            const enabled = editor
                .can()
                .chain()
                .focus()
                .setEvidence({ id: 1234 })
                .run();
            const active = editor.isActive("evidence");
            return { enabled, active };
        },
    });

    const applyCb = useCallback(
        (id: number | null) => {
            if (id) {
                editor.chain().setEvidence({ id }).run();
            }
            setModalInitial(null);
        },
        [setModalInitial, editor]
    );

    let modal = null;
    if (modalInitial !== null) {
        modal = (
            <EvidenceModal
                editor={editor}
                initialId={modalInitial === "new" ? null : modalInitial}
                setEvidenceId={applyCb}
            />
        );
    }

    const editorEl = editor.view.dom;
    useEffect(() => {
        const evl = () => setModalInitial("new");
        editorEl.addEventListener("openevidencemodal", evl);
        return () => editorEl.removeEventListener("openevidencemodal", evl);
    }, [editorEl]);

    return (
        <>
            <button
                tabIndex={-1}
                title={"Evidence"}
                disabled={!enabled}
                className={active ? "is-active" : undefined}
                onClick={(e) => {
                    e.preventDefault();
                    const active = editor.isActive("evidence");
                    if (active) {
                        setModalInitial(editor.getAttributes("evidence").id);
                    } else {
                        setModalInitial("new");
                    }
                }}
            >
                <FontAwesomeIcon icon={faPaperclip} />
            </button>
            {modal}
        </>
    );
}
