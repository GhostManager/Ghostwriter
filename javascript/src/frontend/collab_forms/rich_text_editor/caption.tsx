import { useId, useState } from "react";
import ReactModal from "react-modal";
import { useCurrentEditor } from "@tiptap/react";
import { MenuItem } from "@szhsin/react-menu";

export default function CaptionButton() {
    const editor = useCurrentEditor().editor!;
    const [modalOpen, setModalOpen] = useState(false);
    const [refName, setRefName] = useState("");
    const fieldId = useId();

    const enabled = editor.can().setCaption("refname");

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
                className="modal-dialog modal-dialog-centered"
            >
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title">Insert Caption</h5>
                    </div>
                    <form
                        className="modal-body text-center"
                        onSubmit={(ev) => {
                            ev.preventDefault();
                            editor.chain().setCaption(refName.trim()).run();
                            setModalOpen(false);
                        }}
                    >
                        <div className="form-group">
                            <label htmlFor={fieldId}>
                                Reference Name (Optional)
                            </label>
                            <input
                                id={fieldId}
                                type="text"
                                className="form-control"
                                value={refName}
                                autoFocus
                                onChange={(e) => setRefName(e.target.value)}
                            />
                            <small className="form-text text-muted">
                                If supplied, links can be made to this caption
                                by using <code>{"{{.ref name}}"}</code>
                            </small>
                        </div>

                        <div className="modal-footer">
                            <button className="btn btn-primary">Insert</button>
                            <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={(e) => {
                                    e.preventDefault();
                                    setModalOpen(false);
                                }}
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            </ReactModal>
        </>
    );
}
