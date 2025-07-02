import { useId, useState } from "react";
import { HeadingWithId } from "../../../tiptap_gw/heading";
import ReactModal from "react-modal";
import { useCurrentEditor } from "@tiptap/react";
import { MenuItem } from "@szhsin/react-menu";

export default function HeadingIdButton() {
    const editor = useCurrentEditor().editor!;
    const [modalOpen, setModalOpen] = useState(false);
    const [bookmark, setBookmark] = useState("");
    const fieldId = useId();

    const enabled = editor.can().setHeadingBookmark("example");

    return (
        <>
            <MenuItem
                title="Heading Bookmark"
                disabled={!enabled}
                onClick={() => {
                    setBookmark(
                        editor.getAttributes(HeadingWithId.name).id || ""
                    );
                    setModalOpen(true);
                }}
            >
                Set Bookmark
            </MenuItem>
            <ReactModal
                isOpen={modalOpen}
                onRequestClose={() => setModalOpen(false)}
                contentLabel="Edit Heading Bookmark"
                className="modal-dialog modal-dialog-centered"
            >
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title">Edit Heading Bookmark</h5>
                    </div>
                    <div className="modal-body text-center">
                        <div className="form-group">
                            <label htmlFor={fieldId}>Bookmark Name</label>
                            <input
                                id={fieldId}
                                type="text"
                                className="form-control"
                                value={bookmark}
                                onChange={(e) => setBookmark(e.target.value)}
                            />
                        </div>

                        <div className="modal-footer">
                            <button
                                className="btn btn-primary"
                                onClick={(e) => {
                                    e.preventDefault();
                                    const trimmedId = bookmark.trim();
                                    editor
                                        .chain()
                                        .setHeadingBookmark(
                                            trimmedId === ""
                                                ? undefined
                                                : trimmedId
                                        )
                                        .run();
                                    setModalOpen(false);
                                }}
                            >
                                Save
                            </button>
                            <button
                                className="btn btn-secondary"
                                onClick={(e) => {
                                    e.preventDefault();
                                    setModalOpen(false);
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
