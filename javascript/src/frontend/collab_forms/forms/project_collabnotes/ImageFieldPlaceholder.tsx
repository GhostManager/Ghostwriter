import { useRef, useState, useCallback, useEffect } from "react";

interface ImageFieldPlaceholderProps {
    onUpload: (file: File) => void;
    uploading: boolean;
}

export default function ImageFieldPlaceholder({
    onUpload,
    uploading,
}: ImageFieldPlaceholderProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [dragActive, setDragActive] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const handleFileSelect = useCallback(
        (file: File) => {
            if (file && file.type.startsWith("image/")) {
                onUpload(file);
            }
        },
        [onUpload]
    );

    const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleFileSelect(file);
        }
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

    const handlePaste = useCallback(
        (event: ClipboardEvent) => {
            const items = event.clipboardData?.items;
            if (!items) return;

            for (let i = 0; i < items.length; i++) {
                const item = items[i];
                if (item.type.indexOf("image") !== -1) {
                    event.preventDefault();
                    const file = item.getAsFile();
                    if (file) {
                        handleFileSelect(file);
                    }
                    break;
                }
            }
        },
        [handleFileSelect]
    );

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const handlePasteEvent = (e: Event) => handlePaste(e as ClipboardEvent);
        container.addEventListener("paste", handlePasteEvent);

        return () => {
            container.removeEventListener("paste", handlePasteEvent);
        };
    }, [handlePaste]);

    const handleClick = () => {
        if (!uploading) {
            fileInputRef.current?.click();
        }
    };

    return (
        <div
            ref={containerRef}
            tabIndex={0}
            onClick={handleClick}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "2rem",
                minHeight: "150px",
                border: `2px dashed ${dragActive ? "var(--bs-primary)" : "var(--bs-border-color)"}`,
                borderRadius: "8px",
                backgroundColor: dragActive
                    ? "var(--bs-primary-bg-subtle)"
                    : "var(--bs-tertiary-bg)",
                cursor: uploading ? "wait" : "pointer",
                transition: "all 0.2s ease",
                outline: "none",
            }}
        >
            {uploading ? (
                <>
                    <i
                        className="fas fa-spinner fa-spin"
                        style={{
                            fontSize: "24px",
                            color: "var(--bs-primary)",
                            marginBottom: "8px",
                        }}
                    ></i>
                    <span style={{ color: "var(--bs-secondary-color)" }}>
                        Uploading...
                    </span>
                </>
            ) : (
                <>
                    <i
                        className="fas fa-image"
                        style={{
                            fontSize: "32px",
                            color: dragActive
                                ? "var(--bs-primary)"
                                : "var(--bs-secondary-color)",
                            marginBottom: "12px",
                        }}
                    ></i>
                    <span
                        style={{
                            color: "var(--bs-secondary-color)",
                            textAlign: "center",
                        }}
                    >
                        {dragActive
                            ? "Drop image here"
                            : "Paste, drag-drop, or click to upload"}
                    </span>
                    <span
                        style={{
                            fontSize: "12px",
                            color: "var(--bs-secondary-color)",
                            marginTop: "4px",
                        }}
                    >
                        PNG, JPG, GIF, WebP (max 10 MB)
                    </span>
                </>
            )}

            <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
                onChange={handleFileInputChange}
                style={{ display: "none" }}
            />
        </div>
    );
}
