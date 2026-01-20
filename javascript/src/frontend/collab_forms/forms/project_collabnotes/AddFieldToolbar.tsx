interface AddFieldToolbarProps {
    onAddRichText: () => void;
    onAddImage: () => void;
}

export default function AddFieldToolbar({
    onAddRichText,
    onAddImage,
}: AddFieldToolbarProps) {
    return (
        <div
            className="add-field-toolbar"
            style={{
                display: "flex",
                gap: "8px",
                padding: "12px",
                borderTop: "1px solid var(--bs-border-color)",
                borderBottom: "1px solid var(--bs-border-color)",
                marginBottom: "16px",
                backgroundColor: "var(--bs-tertiary-bg)",
            }}
        >
            <button
                onClick={onAddRichText}
                className="btn btn-sm btn-primary"
                title="Add rich text field"
            >
                <i className="fas fa-plus"></i> Add Text
            </button>

            <button
                onClick={onAddImage}
                className="btn btn-sm btn-primary"
                title="Add image placeholder"
            >
                <i className="fas fa-image"></i> Add Image
            </button>
        </div>
    );
}
