import { useEffect, useState, useCallback } from "react";
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent,
} from "@dnd-kit/core";
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import * as Y from "yjs";
import {
    ConnectionStatus,
    usePageConnection,
} from "../../connection";
import NoteFieldEditor from "./NoteFieldEditor";
import AddFieldToolbar from "./AddFieldToolbar";
import DeleteConfirmModal from "./DeleteConfirmModal";
import { useFieldMutations } from "./hooks/useFieldMutations";
import { useImageUpload } from "./hooks/useImageUpload";
import type { NoteField } from "./types";

interface NoteEditorProps {
    noteId: number;
}

export default function NoteEditor({ noteId }: NoteEditorProps) {
    const { provider, status, connected } = usePageConnection({
        model: "project_collab_note",
        id: noteId.toString(),
    });

    const [fields, setFields] = useState<NoteField[]>([]);
    const [pendingDeleteField, setPendingDeleteField] = useState<NoteField | null>(null);
    const { createRichTextField, deleteField, reorderFields } = useFieldMutations();
    const { uploading, error, uploadImage, handlePaste } = useImageUpload();

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8, // Require 8px movement before drag starts
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // Sync fields from Yjs document meta
    useEffect(() => {
        if (!connected) return;

        const meta = provider.document.getMap("meta");
        let fieldsArray: Y.Array<NoteField> | null = null;
        let fieldsObserver: (() => void) | null = null;

        const updateFields = () => {
            const currentFieldsArray = meta.get("fields") as Y.Array<NoteField> | undefined;
            if (currentFieldsArray) {
                const fieldsList: NoteField[] = [];
                for (let i = 0; i < currentFieldsArray.length; i++) {
                    fieldsList.push(currentFieldsArray.get(i));
                }
                setFields(fieldsList);

                // If the fields array changed, update the observer
                if (currentFieldsArray !== fieldsArray) {
                    // Remove old observer if exists
                    if (fieldsArray && fieldsObserver) {
                        fieldsArray.unobserve(fieldsObserver);
                    }
                    // Observe the new fields array for changes (add/remove items)
                    fieldsArray = currentFieldsArray;
                    fieldsObserver = () => updateFields();
                    fieldsArray.observe(fieldsObserver);
                }
            } else {
                setFields([]);
            }
        };

        // Initial update
        updateFields();

        // Listen for changes to meta (e.g., when fields array is first created)
        const metaObserver = () => updateFields();
        meta.observe(metaObserver);

        return () => {
            meta.unobserve(metaObserver);
            if (fieldsArray && fieldsObserver) {
                fieldsArray.unobserve(fieldsObserver);
            }
        };
    }, [provider, connected]);

    // Helper to sync field additions to Yjs document
    const addFieldToYjsDoc = useCallback(
        (fieldId: string, fieldType: string, position: number, image: string | null = null) => {
            if (!connected) return;
            const meta = provider.document.getMap("meta");
            const existingFields = meta.get("fields") as Y.Array<NoteField> | undefined;

            const newField: NoteField = {
                id: fieldId,
                fieldType,
                image,
                position,
            };

            if (existingFields) {
                existingFields.push([newField]);
            } else {
                const newFieldsArray = new Y.Array<NoteField>();
                newFieldsArray.push([newField]);
                meta.set("fields", newFieldsArray);
            }
        },
        [provider, connected]
    );

    // Helper to remove field from Yjs document
    const removeFieldFromYjsDoc = useCallback(
        (fieldId: string) => {
            if (!connected) return;
            const meta = provider.document.getMap("meta");
            const existingFields = meta.get("fields") as Y.Array<NoteField> | undefined;

            if (existingFields) {
                for (let i = 0; i < existingFields.length; i++) {
                    const field = existingFields.get(i);
                    if (field && field.id === fieldId) {
                        existingFields.delete(i, 1);
                        break;
                    }
                }
            }
        },
        [provider, connected]
    );

    // Handle clipboard paste for images
    useEffect(() => {
        const handlePasteEvent = async (event: ClipboardEvent) => {
            const result = await handlePaste(noteId, event);
            if (result) {
                // Update local state directly for immediate UI feedback
                const newField: NoteField = {
                    id: result.id,
                    fieldType: "image",
                    image: result.imageUrl,
                    position: result.position,
                };
                setFields((prev) => [...prev, newField]);
                // Also sync to Yjs document for other clients
                addFieldToYjsDoc(result.id, "image", result.position, result.imageUrl);
                console.log("Image uploaded via paste:", result);
            }
        };

        document.addEventListener("paste", handlePasteEvent);
        return () => {
            document.removeEventListener("paste", handlePasteEvent);
        };
    }, [noteId, handlePaste, addFieldToYjsDoc]);

    const handleAddRichText = useCallback(async () => {
        try {
            const result = await createRichTextField(noteId);
            // Update local state directly for immediate UI feedback
            const newField: NoteField = {
                id: result.id,
                fieldType: "rich_text",
                image: null,
                position: result.position,
            };
            setFields((prev) => [...prev, newField]);
            // Also sync to Yjs document for other clients
            addFieldToYjsDoc(result.id, "rich_text", result.position);
            console.log("Created rich text field:", result);
        } catch (err) {
            console.error("Failed to create rich text field:", err);
        }
    }, [noteId, createRichTextField, addFieldToYjsDoc]);

    const handleAddImage = useCallback(
        async (file: File) => {
            try {
                const result = await uploadImage(noteId, file);
                if (result) {
                    // Update local state directly for immediate UI feedback
                    const newField: NoteField = {
                        id: result.id,
                        fieldType: "image",
                        image: result.imageUrl,
                        position: result.position,
                    };
                    setFields((prev) => [...prev, newField]);
                    // Also sync to Yjs document for other clients
                    addFieldToYjsDoc(result.id, "image", result.position, result.imageUrl);
                    console.log("Image uploaded:", result);
                }
            } catch (err) {
                console.error("Failed to upload image:", err);
            }
        },
        [noteId, uploadImage, addFieldToYjsDoc]
    );

    const requestDeleteField = useCallback(
        (field: NoteField) => {
            setPendingDeleteField(field);
        },
        []
    );

    const handleConfirmDelete = useCallback(
        async () => {
            if (!pendingDeleteField) return;
            const fieldId = pendingDeleteField.id;
            setPendingDeleteField(null);
            try {
                await deleteField(fieldId);
                // Update local state directly for immediate UI feedback
                setFields((prev) => prev.filter((f) => f.id !== fieldId));
                // Also sync to Yjs document for other clients
                removeFieldFromYjsDoc(fieldId);
            } catch (err) {
                console.error("Failed to delete field:", err);
            }
        },
        [pendingDeleteField, deleteField, removeFieldFromYjsDoc]
    );

    const handleCancelDelete = useCallback(() => {
        setPendingDeleteField(null);
    }, []);

    const handleDragEnd = useCallback(
        async (event: DragEndEvent) => {
            const { active, over } = event;

            if (!over || active.id === over.id) {
                return;
            }

            const oldIndex = fields.findIndex((f) => f.id === active.id);
            const newIndex = fields.findIndex((f) => f.id === over.id);

            if (oldIndex === -1 || newIndex === -1) return;

            const newFields = arrayMove(fields, oldIndex, newIndex);

            // Update positions
            const updates = newFields.map((field, index) => ({
                id: field.id,
                position: index * 1000,
                noteId,
            }));

            setFields(newFields);

            try {
                await reorderFields(updates);
            } catch (err) {
                console.error("Failed to reorder fields:", err);
                // Revert on error
                setFields(fields);
            }
        },
        [fields, noteId, reorderFields]
    );

    return (
        <div className="note-editor-container">
            <ConnectionStatus status={status} />

            {error && (
                <div className="alert alert-danger" role="alert">
                    {error}
                </div>
            )}

            <AddFieldToolbar
                onAddRichText={handleAddRichText}
                onAddImage={handleAddImage}
                uploading={uploading}
            />

            <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
            >
                <SortableContext
                    items={fields.map((f) => f.id)}
                    strategy={verticalListSortingStrategy}
                >
                    {fields.map((field) => (
                        <NoteFieldEditor
                            key={field.id}
                            field={field}
                            provider={provider}
                            connected={connected}
                            onDelete={() => requestDeleteField(field)}
                        />
                    ))}
                </SortableContext>
            </DndContext>

            {fields.length === 0 && connected && (
                <div
                    style={{
                        padding: "2rem",
                        textAlign: "center",
                        color: "#666",
                        fontSize: "14px",
                    }}
                >
                    No fields yet. Add a text field or image above to get started.
                </div>
            )}

            <DeleteConfirmModal
                isOpen={pendingDeleteField !== null}
                fieldType={pendingDeleteField?.fieldType as "rich_text" | "image" | null}
                onClose={handleCancelDelete}
                onConfirm={handleConfirmDelete}
            />
        </div>
    );
}
