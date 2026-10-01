import { useId, useState } from "react";
import ReactModal from "react-modal";
import { Editor, useEditorState } from "@tiptap/react";
import { MenuItem } from "@szhsin/react-menu";

export default function CaptionButton({ editor }: { editor: Editor }) {
    const [modalOpen, setModalOpen] = useState(false);
    const [refName, setRefName] = useState("");
    const fieldId = useId();

    const enabled = useEditorState({
        editor,
        selector: ({ editor }) => editor.can().setCaption("refname"),
    });

    return (
        <>
            <MenuItem
                title="Caption"
                disabled={!enabled}
                onClick={() => {
                    setRefName("");
                    setModalOpen(true);
                }}
            >
                Insert Caption
            </MenuItem>
            <ReactModal
                isOpen={modalOpen}
                onRequestClose={() => setModalOpen(false)}
                contentLabel="Insert Caption"
                className="modal-dialog modal-dialog-centered gw-editor-dialog"
            >
                <div className="modal-content gw-editor-dialog-content">
                    <div className="modal-header gw-editor-dialog-header">
                        <div>
                            <span className="gw-editor-dialog-eyebrow">
                                Report structure
                            </span>
                            <h5 className="modal-title">Insert caption</h5>
                            <p className="gw-editor-dialog-intro">
                                Create a numbered caption at the current
                                position in the report.
                            </p>
                        </div>
                        <button
                            type="button"
                            className="gw-editor-dialog-close"
                            aria-label="Close caption dialog"
                            onClick={() => setModalOpen(false)}
                        >
                            <i className="fas fa-times" aria-hidden="true" />
                        </button>
                    </div>
                    <form
                        className="gw-editor-dialog-form"
                        onSubmit={(ev) => {
                            ev.preventDefault();
                            editor.chain().setCaption(refName.trim()).run();
                            setModalOpen(false);
                        }}
                    >
                        <div className="modal-body gw-editor-dialog-body">
                            <div className="gw-editor-dialog-field">
                                <label htmlFor={fieldId}>
                                    Reference name
                                    <span className="gw-editor-dialog-optional">
                                        Optional
                                    </span>
                                </label>
                                <input
                                    id={fieldId}
                                    type="text"
                                    className="form-control"
                                    value={refName}
                                    autoFocus
                                    onChange={(e) => setRefName(e.target.value)}
                                    placeholder="e.g., authentication-flow"
                                />
                                <small className="form-text">
                                    Use a short name if you want to link to this
                                    caption later with{" "}
                                    <code>{"{{.ref name}}"}</code>.
                                </small>
                            </div>
                        </div>

                        <div className="modal-footer gw-editor-dialog-footer">
                            <button
                                type="button"
                                className="btn btn-outline-secondary"
                                onClick={(e) => {
                                    e.preventDefault();
                                    setModalOpen(false);
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="btn gw-editor-primary-action"
                            >
                                <i
                                    className="fas fa-bookmark"
                                    aria-hidden="true"
                                />
                                Insert caption
                            </button>
                        </div>
                    </form>
                </div>
            </ReactModal>
        </>
    );
}
