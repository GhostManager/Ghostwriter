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
        if (file) handleFileSelect(file);
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
        if (file) handleFileSelect(file);
    };

    const handlePaste = useCallback(
        (event: ClipboardEvent) => {
            const items = event.clipboardData?.items;
            if (!items) return;
            for (let i = 0; i < items.length; i++) {
                if (items[i].type.startsWith("image/")) {
                    event.preventDefault();
                    const file = items[i].getAsFile();
                    if (file) handleFileSelect(file);
                    break;
                }
            }
        },
        [handleFileSelect]
    );

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;
        container.addEventListener("paste", handlePaste);
        return () => container.removeEventListener("paste", handlePaste);
    }, [handlePaste]);

    const handleClick = () => {
        if (!uploading) fileInputRef.current?.click();
    };

    const className = [
        "image-field-placeholder",
        dragActive && "drag-active",
        uploading && "uploading",
    ].filter(Boolean).join(" ");

    return (
        <div
            ref={containerRef}
            tabIndex={0}
            onClick={handleClick}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={className}
        >
            {uploading ? (
                <>
                    <i className="fas fa-spinner fa-spin image-field-placeholder__icon"></i>
                    <span className="image-field-placeholder__text">Uploading...</span>
                </>
            ) : (
                <>
                    <i className="fas fa-image image-field-placeholder__icon"></i>
                    <span className="image-field-placeholder__text">
                        {dragActive ? "Drop image here" : "Paste, drag-drop, or click to upload"}
                    </span>
                    <span className="image-field-placeholder__hint">
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
