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
                className="modal-dialog modal-dialog-centered gw-editor-dialog"
            >
                <div className="modal-content gw-editor-dialog-content">
                    <div className="modal-header gw-editor-dialog-header">
                        <div>
                            <span className="gw-editor-dialog-eyebrow">
                                Report annotation
                            </span>
                            <h5 className="modal-title">Insert footnote</h5>
                            <p className="gw-editor-dialog-intro">
                                Add supporting context without interrupting the
                                main narrative.
                            </p>
                        </div>
                        <button
                            type="button"
                            className="gw-editor-dialog-close"
                            aria-label="Close footnote dialog"
                            onClick={() => setModalOpen(false)}
                        >
                            <i className="fas fa-times" aria-hidden="true" />
                        </button>
                    </div>
                    <form
                        className="gw-editor-dialog-form"
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
                        <div className="modal-body gw-editor-dialog-body">
                            <div className="gw-editor-dialog-field">
                                <label htmlFor={fieldId}>Footnote text</label>
                                <textarea
                                    id={fieldId}
                                    className="form-control no-auto-rich-text"
                                    rows={4}
                                    value={footnoteContent}
                                    autoFocus
                                    onChange={(e) =>
                                        setFootnoteContent(e.target.value)
                                    }
                                    placeholder="Enter the supporting context..."
                                />
                                <small className="form-text">
                                    This text appears at the bottom of the page
                                    in the generated report.
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
                                disabled={!footnoteContent.trim()}
                            >
                                <i
                                    className="fas fa-superscript"
                                    aria-hidden="true"
                                />
                                Insert footnote
                            </button>
                        </div>
                    </form>
                </div>
            </ReactModal>
        </>
    );
}
