import { useState } from "react";
import ImageFieldPlaceholder from "./ImageFieldPlaceholder";

interface ImageFieldProps {
    imageUrl: string | null | undefined;
    onDelete: () => void;
    onUpload?: (file: File) => void;
    uploading?: boolean;
}

export default function ImageField({
    imageUrl,
    onDelete,
    onUpload,
    uploading = false,
}: ImageFieldProps) {
    const [showDeleteOverlay, setShowDeleteOverlay] = useState(false);

    if (!imageUrl) {
        return (
            <ImageFieldPlaceholder
                onUpload={onUpload || (() => {})}
                uploading={uploading}
            />
        );
    }

    return (
        <div
            className="note-field-image-container"
            onMouseEnter={() => setShowDeleteOverlay(true)}
            onMouseLeave={() => setShowDeleteOverlay(false)}
            style={{
                position: "relative",
                marginBottom: "1rem",
            }}
        >
            <img
                src={imageUrl}
                alt="Note attachment"
                className="note-field-image"
                style={{
                    maxWidth: "100%",
                    maxHeight: "400px",
                    objectFit: "contain",
                    display: "block",
                    borderRadius: "4px",
                    border: "1px solid #ddd",
                }}
            />
            {showDeleteOverlay && (
                <div
                    style={{
                        position: "absolute",
                        top: "8px",
                        right: "8px",
                    }}
                >
                    <button
                        onClick={onDelete}
                        className="btn btn-sm btn-danger"
                        title="Delete image"
                        style={{
                            padding: "4px 8px",
                            fontSize: "12px",
                        }}
                    >
                        <i className="fas fa-trash"></i>
                    </button>
                </div>
            )}
        </div>
    );
}
