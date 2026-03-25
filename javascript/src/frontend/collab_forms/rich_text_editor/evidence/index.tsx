import { faPaperclip } from "@fortawesome/free-solid-svg-icons/faPaperclip";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Editor } from "@tiptap/core";
import { useCallback, useEffect, useState } from "react";
import EvidenceModal from "./modal";
import { useEditorState } from "@tiptap/react";

// null = closed, "new" = inserting, number = editing existing, { file } = paste-triggered upload
type ModalState = null | "new" | number | { file: File };

export default function EvidenceButton({ editor }: { editor: Editor }) {
    const [modalState, setModalState] = useState<ModalState>(null);

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
            setModalState(null);
        },
        [setModalState, editor]
    );

    let modal = null;
    if (modalState !== null) {
        const initialId =
            typeof modalState === "number" ? modalState : null;
        const initialFile =
            typeof modalState === "object" ? modalState.file : undefined;
        modal = (
            <EvidenceModal
                editor={editor}
                initialId={initialId}
                initialFile={initialFile}
                setEvidenceId={applyCb}
            />
        );
    }

    const editorEl = editor.view.dom;
    useEffect(() => {
        const handleOpenModal = () => setModalState("new");
        const handlePaste = (ev: ClipboardEvent) => {
            const files = ev.clipboardData?.files;
            if (!files || files.length !== 1) return;
            const file = files[0];
            if (!file.type.match(/^image\/(png|jpeg)$/)) return;
            ev.preventDefault();
            setModalState({ file });
        };
        editorEl.addEventListener("openevidencemodal", handleOpenModal);
        // Capture phase so we intercept before ProseMirror's paste handler
        editorEl.addEventListener("paste", handlePaste, { capture: true });
        return () => {
            editorEl.removeEventListener("openevidencemodal", handleOpenModal);
            editorEl.removeEventListener("paste", handlePaste, { capture: true });
        };
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
                        setModalState(editor.getAttributes("evidence").id);
                    } else {
                        setModalState("new");
                    }
                }}
            >
                <FontAwesomeIcon icon={faPaperclip} />
            </button>
            {modal}
        </>
    );
}
