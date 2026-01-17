import { useState } from "react";

interface UploadImageResponse {
    result: string;
    id: string;
    imageUrl: string;
    position: number;
    message?: string;
}

interface UseImageUploadReturn {
    uploading: boolean;
    error: string | null;
    uploadImage: (noteId: number, file: File) => Promise<UploadImageResponse | null>;
    handlePaste: (noteId: number, event: ClipboardEvent) => Promise<UploadImageResponse | null>;
}

export function useImageUpload(): UseImageUploadReturn {
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const uploadImage = async (noteId: number, file: File): Promise<UploadImageResponse | null> => {
        setUploading(true);
        setError(null);

        try {
            // Validate file type
            const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
            if (!allowedTypes.includes(file.type)) {
                throw new Error(`Invalid file type: ${file.type}. Allowed types: png, jpg, jpeg, gif, webp`);
            }

            // Validate file size (10 MB max)
            const maxSize = 10 * 1024 * 1024;
            if (file.size > maxSize) {
                throw new Error(`File too large: ${(file.size / 1024 / 1024).toFixed(1)} MB. Maximum size: 10 MB`);
            }

            const formData = new FormData();
            formData.append('image', file);

            // Get CSRF token from cookie
            const csrf = document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];

            const response = await fetch(`/rolodex/ajax/note/${noteId}/field/image`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrf || '',
                },
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.message || 'Failed to upload image');
            }

            const data: UploadImageResponse = await response.json();

            if (data.result !== 'success') {
                throw new Error(data.message || 'Upload failed');
            }

            return data;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
            setError(errorMessage);
            console.error('Image upload error:', err);
            return null;
        } finally {
            setUploading(false);
        }
    };

    const handlePaste = async (noteId: number, event: ClipboardEvent): Promise<UploadImageResponse | null> => {
        const items = event.clipboardData?.items;
        if (!items) return null;

        // Look for image items in clipboard
        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            if (item.type.indexOf('image') !== -1) {
                event.preventDefault();
                const file = item.getAsFile();
                if (file) {
                    return await uploadImage(noteId, file);
                }
            }
        }

        return null;
    };

    return {
        uploading,
        error,
        uploadImage,
        handlePaste,
    };
}
