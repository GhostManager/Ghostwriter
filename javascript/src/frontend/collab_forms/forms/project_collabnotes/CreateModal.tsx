import { useState } from "react";
import ReactModal from "react-modal";

interface CreateModalProps {
    isOpen: boolean;
    type: "note" | "folder";
    onClose: () => void;
    onCreate: (title: string) => void;
}

export default function CreateModal({
    isOpen,
    type,
    onClose,
    onCreate,
}: CreateModalProps) {
    const [title, setTitle] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim()) return;

        setIsSubmitting(true);
        try {
            await onCreate(title.trim());
            setTitle("");
            onClose();
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleClose = () => {
        setTitle("");
        onClose();
    };

    return (
        <ReactModal
            isOpen={isOpen}
            onRequestClose={handleClose}
            className="modal-dialog modal-dialog-centered"
            overlayClassName="modal-backdrop-custom"
            style={{
                overlay: {
                    position: "fixed",
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: "rgba(0, 0, 0, 0.5)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    zIndex: 1050,
                },
                content: {
                    position: "relative",
                    inset: "auto",
                    border: "none",
                    background: "none",
                    padding: 0,
                    maxWidth: "500px",
                    width: "100%",
                },
            }}
        >
            <div className="modal-content">
                <div className="modal-header">
                    <h5 className="modal-title">
                        Create New {type === "folder" ? "Folder" : "Note"}
                    </h5>
                    <button
                        type="button"
                        className="btn-close"
                        onClick={handleClose}
                        aria-label="Close"
                    ></button>
                </div>
                <form onSubmit={handleSubmit}>
                    <div className="modal-body">
                        <div className="mb-3">
                            <label htmlFor="noteTitle" className="form-label">
                                Title
                            </label>
                            <input
                                type="text"
                                className="form-control"
                                id="noteTitle"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder={`Enter ${type} title...`}
                                autoFocus
                                required
                            />
                        </div>
                    </div>
                    <div className="modal-footer">
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={handleClose}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={!title.trim() || isSubmitting}
                        >
                            {isSubmitting ? "Creating..." : "Create"}
                        </button>
                    </div>
                </form>
            </div>
        </ReactModal>
    );
}
