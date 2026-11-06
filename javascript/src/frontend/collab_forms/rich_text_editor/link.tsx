import { faLink } from "@fortawesome/free-solid-svg-icons/faLink";
import { faXmark } from "@fortawesome/free-solid-svg-icons/faXmark";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Editor } from "@tiptap/core";
import { useEditorState } from "@tiptap/react";
import { useId, useRef, useState } from "react";
import ReactModal from "react-modal";
import { sanitizeLinkHref } from "../../../tiptap_gw/link";

export default function LinkButton({ editor }: { editor: Editor }) {
    const [modalMode, setModalMode] = useState<null | "new" | "edit">(null);
    const [formUrl, setFormUrl] = useState("");
    const [validationError, setValidationError] = useState<string | null>(null);
    const urlId = useId();
    const titleId = useId();
    const helpId = useId();
    const errorId = useId();
    const urlInput = useRef<HTMLInputElement>(null);

    const { enabled, active } = useEditorState({
        editor,
        selector: ({ editor }) => {
            if (!editor.isInitialized) return { enabled: false, active: false };
            const enabled = editor
                .can()
                .chain()
                .focus()
                .setLink({ href: "https://example.com" })
                .run();
            const active = editor.isActive("link");
            return { enabled, active };
        },
    });

    return (
        <>
            <button
                tabIndex={-1}
                title="Link"
                type="button"
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
                    setValidationError(null);
                    setModalMode(active ? "edit" : "new");
                }}
            >
                <FontAwesomeIcon icon={faLink} />
            </button>
            <ReactModal
                isOpen={!!modalMode}
                onAfterOpen={() => urlInput.current?.focus()}
                onRequestClose={() => setModalMode(null)}
                contentLabel="Edit Link"
                aria={{ labelledby: titleId }}
                className="modal-dialog modal-dialog-centered gw-editor-dialog"
            >
                <div className="modal-content gw-editor-dialog-content">
                    <div className="modal-header gw-editor-dialog-header">
                        <div>
                            <span className="gw-editor-dialog-eyebrow">
                                Rich text
                            </span>
                            <h5 id={titleId} className="modal-title">
                                Edit Link
                            </h5>
                            <p className="gw-editor-dialog-intro">
                                Set the destination for the selected text.
                            </p>
                        </div>
                        <button
                            type="button"
                            className="gw-editor-dialog-close"
                            aria-label="Close link dialog"
                            onClick={() => setModalMode(null)}
                        >
                            <FontAwesomeIcon
                                icon={faXmark}
                                aria-hidden="true"
                            />
                        </button>
                    </div>
                    <form
                        className="gw-editor-dialog-form"
                        onSubmit={(ev) => {
                            ev.preventDefault();
                            if (formUrl) {
                                const sanitizedHref = sanitizeLinkHref(formUrl);
                                if (!sanitizedHref) {
                                    setValidationError(
                                        "Use a relative URL, anchor, or an http, https, mailto, or tel link."
                                    );
                                    return;
                                }
                                editor
                                    .chain()
                                    .focus()
                                    .setLink({ href: sanitizedHref })
                                    .run();
                            }
                            setValidationError(null);
                            setModalMode(null);
                        }}
                    >
                        <div className="modal-body gw-editor-dialog-body">
                            <div className="gw-editor-dialog-field">
                                <label htmlFor={urlId}>URL</label>
                                <input
                                    id={urlId}
                                    ref={urlInput}
                                    type="text"
                                    className="form-control"
                                    value={formUrl}
                                    autoFocus
                                    aria-invalid={!!validationError}
                                    aria-describedby={
                                        validationError
                                            ? `${helpId} ${errorId}`
                                            : helpId
                                    }
                                    placeholder="https://example.com"
                                    onChange={(e) => {
                                        setFormUrl(e.target.value);
                                        setValidationError(null);
                                    }}
                                />
                                <small id={helpId} className="form-text">
                                    Use a web address, relative URL, anchor,
                                    email address (mailto:), or phone number
                                    (tel:).
                                </small>
                            </div>
                            {validationError && (
                                <div
                                    id={errorId}
                                    className="alert alert-danger gw-editor-dialog-alert"
                                    role="alert"
                                >
                                    {validationError}
                                </div>
                            )}
                        </div>

                        <div className="modal-footer gw-editor-dialog-footer">
                            {modalMode === "edit" && (
                                <button
                                    type="button"
                                    className="btn btn-outline-danger me-auto"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        editor.chain().unsetLink().run();
                                        setValidationError(null);
                                        setModalMode(null);
                                    }}
                                >
                                    Remove link
                                </button>
                            )}
                            <button
                                type="button"
                                className="btn btn-outline-secondary"
                                onClick={(e) => {
                                    e.preventDefault();
                                    setValidationError(null);
                                    setModalMode(null);
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="btn gw-editor-primary-action"
                            >
                                Save link
                            </button>
                        </div>
                    </form>
                </div>
            </ReactModal>
        </>
    );
}
