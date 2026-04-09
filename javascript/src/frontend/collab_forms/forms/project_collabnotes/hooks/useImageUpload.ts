import { useState } from "react";

interface UploadImageResponse {
    result: string;
    id: string;
    imageUrl: string;
    position: number;
    message?: string;
}

interface UploadToFieldResponse {
    result: string;
    imageUrl: string;
    message?: string;
}

export function useImageUpload() {
    const [uploading, setUploading] = useState(false);
    const [uploadingFieldId, setUploadingFieldId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const uploadImage = async (noteId: number, file: File): Promise<UploadImageResponse | null> => {
        setUploading(true);
        setError(null);

        try {
            if (!file.type.startsWith("image/")) {
                throw new Error(`Invalid file type: ${file.type}`);
            }

            const maxSize = 10 * 1024 * 1024;
            if (file.size > maxSize) {
                throw new Error(`File too large: ${(file.size / 1024 / 1024).toFixed(1)} MB. Maximum: 10 MB`);
            }

            const formData = new FormData();
            formData.append("image", file);

            const csrf = document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];

            const response = await fetch(`/rolodex/ajax/note/${noteId}/field/image`, {
                method: "POST",
                body: formData,
                headers: { "X-CSRFToken": csrf || "" },
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.message || "Failed to upload image");
            }

            const data: UploadImageResponse = await response.json();
            if (data.result !== "success") throw new Error(data.message || "Upload failed");
            return data;
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unknown error");
            return null;
        } finally {
            setUploading(false);
        }
    };

    const uploadToField = async (
        noteId: number,
        fieldId: string,
        file: File
    ): Promise<UploadToFieldResponse | null> => {
        setUploading(true);
        setUploadingFieldId(fieldId);
        setError(null);

        try {
            if (!file.type.startsWith("image/")) {
                throw new Error(`Invalid file type: ${file.type}`);
            }

            const maxSize = 10 * 1024 * 1024;
            if (file.size > maxSize) {
                throw new Error(`File too large: ${(file.size / 1024 / 1024).toFixed(1)} MB. Maximum: 10 MB`);
            }

            const formData = new FormData();
            formData.append("image", file);

            const csrf = document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];

            const response = await fetch(`/rolodex/ajax/note/${noteId}/field/${fieldId}/image`, {
                method: "POST",
                body: formData,
                headers: { "X-CSRFToken": csrf || "" },
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.message || "Failed to upload image");
            }

            const data: UploadToFieldResponse = await response.json();
            if (data.result !== "success") throw new Error(data.message || "Upload failed");
            return data;
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unknown error");
            return null;
        } finally {
            setUploading(false);
            setUploadingFieldId(null);
        }
    };

    const handlePaste = async (noteId: number, event: ClipboardEvent): Promise<UploadImageResponse | null> => {
        const items = event.clipboardData?.items;
        if (!items) return null;

        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            if (item.type.startsWith("image/")) {
                event.preventDefault();
                const file = item.getAsFile();
                if (file) return await uploadImage(noteId, file);
            }
        }
        return null;
    };

    return { uploading, uploadingFieldId, error, uploadImage, uploadToField, handlePaste };
}
