import { faBookmark } from "@fortawesome/free-solid-svg-icons/faBookmark";
import { faXmark } from "@fortawesome/free-solid-svg-icons/faXmark";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useId, useRef } from "react";
import ReactModal from "react-modal";

export default function BookmarkDialog({
    isOpen,
    target,
    bookmark,
    setBookmark,
    onSave,
    onClose,
}: {
    isOpen: boolean;
    target: "heading" | "table caption";
    bookmark: string;
    setBookmark: (value: string) => void;
    onSave: (value: string | undefined) => void;
    onClose: () => void;
}) {
    const fieldId = useId();
    const titleId = useId();
    const helpId = useId();
    const input = useRef<HTMLInputElement>(null);
    const title =
        target === "heading"
            ? "Edit Heading Bookmark"
            : "Edit Table Caption Bookmark";

    return (
        <ReactModal
            isOpen={isOpen}
            onAfterOpen={() => input.current?.focus()}
            onRequestClose={onClose}
            contentLabel={title}
            aria={{ labelledby: titleId }}
            className="modal-dialog modal-dialog-centered gw-editor-dialog"
        >
            <div className="modal-content gw-editor-dialog-content">
                <div className="modal-header gw-editor-dialog-header">
                    <div>
                        <span className="gw-editor-dialog-eyebrow">
                            Report structure
                        </span>
                        <h5 id={titleId} className="modal-title">
                            {title}
                        </h5>
                        <p className="gw-editor-dialog-intro">
                            Name this {target} so you can reference it in your
                            report.
                        </p>
                    </div>
                    <button
                        type="button"
                        className="gw-editor-dialog-close"
                        aria-label="Close bookmark dialog"
                        onClick={onClose}
                    >
                        <FontAwesomeIcon icon={faXmark} aria-hidden="true" />
                    </button>
                </div>
                <form
                    className="gw-editor-dialog-form"
                    onSubmit={(event) => {
                        event.preventDefault();
                        onSave(bookmark.trim() || undefined);
                        onClose();
                    }}
                >
                    <div className="modal-body gw-editor-dialog-body">
                        <div className="gw-editor-dialog-field">
                            <label htmlFor={fieldId}>
                                Bookmark name
                                <span className="gw-editor-dialog-optional">
                                    Optional
                                </span>
                            </label>
                            <input
                                id={fieldId}
                                ref={input}
                                type="text"
                                className="form-control"
                                value={bookmark}
                                autoFocus
                                aria-describedby={helpId}
                                onChange={(event) =>
                                    setBookmark(event.target.value)
                                }
                            />
                            <small id={helpId} className="form-text">
                                Leave blank to remove the bookmark.
                            </small>
                        </div>
                    </div>
                    <div className="modal-footer gw-editor-dialog-footer">
                        <button
                            type="button"
                            className="btn btn-outline-secondary"
                            onClick={onClose}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="btn gw-editor-primary-action"
                        >
                            <FontAwesomeIcon
                                icon={faBookmark}
                                aria-hidden="true"
                                className="me-2"
                            />
                            Save bookmark
                        </button>
                    </div>
                </form>
            </div>
        </ReactModal>
    );
}
