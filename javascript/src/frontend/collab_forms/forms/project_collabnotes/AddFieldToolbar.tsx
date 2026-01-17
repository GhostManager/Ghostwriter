import { useRef, useState } from "react";

interface AddFieldToolbarProps {
    onAddRichText: () => void;
    onAddImage: (file: File) => void;
    uploading: boolean;
}

export default function AddFieldToolbar({
    onAddRichText,
    onAddImage,
    uploading,
}: AddFieldToolbarProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [dragActive, setDragActive] = useState(false);

    const handleFileSelect = (file: File) => {
        if (file && file.type.startsWith("image/")) {
            onAddImage(file);
        }
    };

    const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleFileSelect(file);
        }
        // Reset input so same file can be selected again
        e.target.value = "";
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        const file = e.dataTransfer.files?.[0];
        if (file) {
            handleFileSelect(file);
        }
    };

    return (
        <div
            className="add-field-toolbar"
            style={{
                display: "flex",
                gap: "8px",
                padding: "12px",
                borderTop: "1px solid #ddd",
                borderBottom: "1px solid #ddd",
                marginBottom: "16px",
                backgroundColor: dragActive ? "#f0f8ff" : "#f8f9fa",
                transition: "background-color 0.2s",
            }}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
        >
            <button
                onClick={onAddRichText}
                className="btn btn-sm btn-primary"
                disabled={uploading}
                title="Add rich text field"
            >
                <i className="fas fa-plus"></i> Add Text
            </button>

            <button
                onClick={() => fileInputRef.current?.click()}
                className="btn btn-sm btn-primary"
                disabled={uploading}
                title="Upload image"
            >
                <i className="fas fa-image"></i> {uploading ? "Uploading..." : "Add Image"}
            </button>

            <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
                onChange={handleFileInputChange}
                style={{ display: "none" }}
            />

            <span
                style={{
                    marginLeft: "auto",
                    fontSize: "12px",
                    color: "#666",
                    alignSelf: "center",
                }}
            >
                {dragActive ? "Drop image here" : "Or drag and drop images"}
            </span>
        </div>
    );
}
