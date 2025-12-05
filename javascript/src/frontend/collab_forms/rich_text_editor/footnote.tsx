import { useId, useState } from "react";
import ReactModal from "react-modal";
import { Editor, useEditorState } from "@tiptap/react";
import { MenuItem } from "@szhsin/react-menu";

export default function FootnoteButton({ editor }: { editor: Editor }) {
    const [modalOpen, setModalOpen] = useState(false);
    const [footnoteContent, setFootnoteContent] = useState("");
    const fieldId = useId();

    const enabled = useEditorState({
        editor,
        selector: ({ editor }) => editor.can().insertFootnote({ content: "" }),
    });

    return (
        <>
            <MenuItem
                title="Insert Footnote"
                disabled={!enabled}
                onClick={() => {
                    setFootnoteContent("");
                    setModalOpen(true);
                }}
            >
                Insert Footnote
            </MenuItem>
            <ReactModal
                isOpen={modalOpen}
                onRequestClose={() => setModalOpen(false)}
                contentLabel="Insert Footnote"
                className="modal-dialog modal-dialog-centered"
            >
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title">Insert Footnote</h5>
                    </div>
                    <form
                        className="modal-body text-center"
                        onSubmit={(ev) => {
                            ev.preventDefault();
                            const content = footnoteContent.trim();
                            if (content) {
                                editor
                                    .chain()
                                    .focus()
                                    .insertFootnote({ content })
                                    .run();
                            }
                            setModalOpen(false);
                        }}
                    >
                        <div className="form-group">
                            <label htmlFor={fieldId}>Footnote Text</label>
                            <textarea
                                id={fieldId}
                                className="form-control"
                                rows={3}
                                value={footnoteContent}
                                autoFocus
                                onChange={(e) =>
                                    setFootnoteContent(e.target.value)
                                }
                                placeholder="Enter the footnote content..."
                            />
                            <small className="form-text text-muted">
                                This text will appear at the bottom of the page
                                in the generated report.
                            </small>
                        </div>

                        <div className="modal-footer">
                            <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={!footnoteContent.trim()}
                            >
                                Insert
                            </button>
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
