import { faPaperclip } from "@fortawesome/free-solid-svg-icons/faPaperclip";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Editor } from "@tiptap/core";
import { useContext, useId, useState } from "react";
import ReactModal from "react-modal";
import { EvidencesContext } from "../../../tiptap_gw/evidence";

export default function EvidenceButton({ editor }: { editor: Editor }) {
    const [modalMode, setModalMode] = useState<null | "new" | "edit">(null);
    const [evidenceId, setEvidenceId] = useState<number | null>(null);
    const nameId = useId();
    const evidences = useContext(EvidencesContext);

    const enabled = editor
        .can()
        .chain()
        .focus()
        .setEvidence({ id: 1234 })
        .run();
    const active = editor.isActive("evidence");

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
                        setEvidenceId(editor.getAttributes("evidence").id);
                    } else {
                        setEvidenceId(null);
                    }
                    setModalMode(active ? "edit" : "new");
                }}
            >
                <FontAwesomeIcon icon={faPaperclip} />
            </button>
            <ReactModal
                isOpen={!!modalMode}
                onRequestClose={() => setModalMode(null)}
                contentLabel="Insert Evidence"
                className="modal-dialog midal-dialog-centered"
            >
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title">
                            {modalMode === "edit" ? "Edit" : "Insert"} Evidence
                        </h5>
                    </div>

                    <div className="modal-body text-center">
                        <div className="form-group">
                            <label htmlFor={nameId}>Evidence Name</label>
                            <select
                                className="custom-select custom-select-lg"
                                value={evidenceId?.toString()}
                                onChange={(e) =>
                                    setEvidenceId(
                                        e.target.value === ""
                                            ? null
                                            : parseInt(e.target.value)
                                    )
                                }
                            >
                                <option value="">Select Evidence...</option>
                                {evidences?.evidence?.map((e) => (
                                    <option value={e.id} key={e.id}>
                                        {e.friendlyName}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="modal-footer">
                            <button
                                className="btn btn-primary"
                                disabled={evidenceId === null}
                                onClick={(e) => {
                                    e.preventDefault();
                                    if (evidenceId !== null)
                                        editor
                                            .chain()
                                            .setEvidence({ id: evidenceId })
                                            .run();
                                    setModalMode(null);
                                }}
                            >
                                Save
                            </button>
                            <button
                                className="btn btn-secondary"
                                onClick={(e) => {
                                    e.preventDefault();
                                    setModalMode(null);
                                }}
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            </ReactModal>
        </>
    );
}
