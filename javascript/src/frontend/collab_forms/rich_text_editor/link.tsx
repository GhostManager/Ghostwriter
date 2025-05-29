import { faLink } from "@fortawesome/free-solid-svg-icons/faLink";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Editor } from "@tiptap/core";
import { useId, useState } from "react";
import ReactModal from "react-modal";

export default function LinkButton(props: { editor: Editor }) {
    const { editor } = props;
    const [modalMode, setModalMode] = useState<null | "new" | "edit">(null);
    const [formUrl, setFormUrl] = useState("");
    const urlId = useId();

    const enabled = editor
        .can()
        .chain()
        .focus()
        .setLink({ href: "https://example.com" })
        .run();
    const active = editor.isActive("link");

    return (
        <>
            <button
                tabIndex={-1}
                title="Link"
                disabled={!enabled}
                className={active ? "is-active" : undefined}
                onClick={(e) => {
                    e.preventDefault();
                    const active = editor.isActive("link");
                    if (active) {
                        editor.chain().focus().extendMarkRange("link").run();
                        setFormUrl(editor.getAttributes("link").href);
                    } else {
                        setFormUrl("");
                    }
                    setModalMode(active ? "edit" : "new");
                }}
            >
                <FontAwesomeIcon icon={faLink} />
            </button>
            <ReactModal
                isOpen={!!modalMode}
                onRequestClose={() => setModalMode(null)}
                contentLabel="Edit Link"
                className="modal-dialog modal-dialog-centered"
            >
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title">Edit Link</h5>
                    </div>
                    <div className="modal-body text-center">
                        <div className="form-group">
                            <label htmlFor={urlId}>URL</label>
                            <input
                                id={urlId}
                                type="url"
                                className="form-control"
                                value={formUrl}
                                onChange={(e) => setFormUrl(e.target.value)}
                            />
                        </div>

                        <div className="modal-footer">
                            <button
                                className="btn btn-primary"
                                onClick={(e) => {
                                    e.preventDefault();
                                    if (formUrl)
                                        editor
                                            .chain()
                                            .setLink({ href: formUrl })
                                            .run();
                                    setModalMode(null);
                                }}
                            >
                                Save
                            </button>
                            {modalMode === "edit" && (
                                <button
                                    className="btn btn-danger"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        editor.chain().unsetLink().run();
                                        setModalMode(null);
                                    }}
                                >
                                    Remove
                                </button>
                            )}
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
