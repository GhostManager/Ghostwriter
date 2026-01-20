import ReactModal from "react-modal";

type DeleteItemType = "rich_text" | "image" | "note" | "folder" | null;

interface DeleteConfirmModalProps {
    isOpen: boolean;
    itemType: DeleteItemType;
    itemTitle?: string;
    onClose: () => void;
    onConfirm: () => void;
}

export default function DeleteConfirmModal({
    isOpen,
    itemType,
    itemTitle,
    onClose,
    onConfirm,
}: DeleteConfirmModalProps) {
    const getTypeLabel = () => {
        switch (itemType) {
            case "rich_text":
                return "text field";
            case "image":
                return "image";
            case "note":
                return "note";
            case "folder":
                return "folder";
            default:
                return "item";
        }
    };

    const typeLabel = getTypeLabel();
    const isFolder = itemType === "folder";

    return (
        <ReactModal
            isOpen={isOpen}
            onRequestClose={onClose}
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
                        <i className="fas fa-exclamation-triangle text-warning me-2"></i>
                        Confirm Delete
                    </h5>
                    <button
                        type="button"
                        className="btn-close"
                        onClick={onClose}
                        aria-label="Close"
                    ></button>
                </div>
                <div className="modal-body">
                    <p>
                        Are you sure you want to delete {itemTitle ? (
                            <>the {typeLabel} <strong>"{itemTitle}"</strong></>
                        ) : (
                            <>this {typeLabel}</>
                        )}?
                    </p>
                    {isFolder && (
                        <p className="text-warning mb-2">
                            <i className="fas fa-exclamation-circle me-1"></i>
                            This will also delete all notes and subfolders inside.
                        </p>
                    )}
                    <p className="text-muted mb-0">
                        <small>This action cannot be undone.</small>
                    </p>
                </div>
                <div className="modal-footer">
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={onClose}
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        className="btn btn-danger"
                        onClick={onConfirm}
                    >
                        Delete
                    </button>
                </div>
            </div>
        </ReactModal>
    );
}
