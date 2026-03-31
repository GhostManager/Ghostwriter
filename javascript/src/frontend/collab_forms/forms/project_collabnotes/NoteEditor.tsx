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

/**
 * NoteEditor derives fields directly from the Yjs document via observeDeep.
 * The Yjs meta.fields Y.Array is the single source of truth for field state.
 * React state is updated only via Yjs observation callbacks.
 */
export default function NoteEditor({ noteId }: NoteEditorProps) {
    const { provider, status, connected } = usePageConnection({
        model: "project_collab_note",
        id: noteId.toString(),
    });

    const [fields, setFields] = useState<NoteField[]>([]);
    const [pendingDeleteField, setPendingDeleteField] = useState<NoteField | null>(null);
    const { createRichTextField, createImageField, deleteField, reorderFields } = useFieldMutations();
    const { uploading, uploadingFieldId, error, uploadImage, uploadToField, handlePaste } = useImageUpload();

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: { distance: 8 },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // Derive fields from Yjs document via observeDeep (Comment #17)
    // The Yjs doc is the single source of truth; React state is read-only derived.
    useEffect(() => {
        if (!connected) return;

        const meta = provider.document.getMap("meta");

        const syncFieldsFromYjs = () => {
            const fieldsArray = meta.get("fields") as Y.Array<NoteField> | undefined;
            if (!fieldsArray) {
                setFields([]);
                return;
            }
            const fieldsList: NoteField[] = [];
            for (let i = 0; i < fieldsArray.length; i++) {
                fieldsList.push(fieldsArray.get(i));
            }
            setFields(fieldsList);
        };

        // Initial sync
        syncFieldsFromYjs();

        // Observe all deep changes to meta (handles fields array creation,
        // item additions/removals, and nested property changes)
        meta.observeDeep(syncFieldsFromYjs);

        return () => {
            meta.unobserveDeep(syncFieldsFromYjs);
        };
    }, [provider, connected]);

    // Helper: mutate the Yjs fields array (all field changes go through here)
    const getFieldsArray = useCallback((): Y.Array<NoteField> | null => {
        if (!connected) return null;
        const meta = provider.document.getMap("meta");
        return (meta.get("fields") as Y.Array<NoteField>) || null;
    }, [provider, connected]);

    const ensureFieldsArray = useCallback((): Y.Array<NoteField> => {
        const meta = provider.document.getMap("meta");
        let arr = meta.get("fields") as Y.Array<NoteField> | undefined;
        if (!arr) {
            arr = new Y.Array<NoteField>();
            meta.set("fields", arr);
        }
        return arr;
    }, [provider]);

    // Clipboard paste for images
    useEffect(() => {
        const handlePasteEvent = async (event: ClipboardEvent) => {
            const result = await handlePaste(noteId, event);
            if (result) {
                const newField: NoteField = {
                    id: result.id,
                    fieldType: "image",
                    image: result.imageUrl,
                    position: result.position,
                };
                const arr = ensureFieldsArray();
                arr.push([newField]);
            }
        };

        document.addEventListener("paste", handlePasteEvent);
        return () => document.removeEventListener("paste", handlePasteEvent);
    }, [noteId, handlePaste, ensureFieldsArray]);

    const handleAddRichText = useCallback(async () => {
        try {
            const result = await createRichTextField(noteId);
            const newField: NoteField = {
                id: result.id,
                fieldType: "rich_text",
                image: null,
                position: result.position,
            };
            const arr = ensureFieldsArray();
            arr.push([newField]);
        } catch (err) {
            console.error("Failed to create rich text field:", err);
        }
    }, [noteId, createRichTextField, ensureFieldsArray]);

    const handleAddImage = useCallback(async () => {
        try {
            const result = await createImageField(noteId);
            const newField: NoteField = {
                id: result.id,
                fieldType: "image",
                image: null,
                position: result.position,
            };
            const arr = ensureFieldsArray();
            arr.push([newField]);
        } catch (err) {
            console.error("Failed to create image field:", err);
        }
    }, [noteId, createImageField, ensureFieldsArray]);

    const handleUploadToField = useCallback(
        async (fieldId: string, file: File) => {
            try {
                const result = await uploadToField(noteId, fieldId, file);
                if (result) {
                    const arr = getFieldsArray();
                    if (arr) {
                        provider.document.transact(() => {
                            for (let i = 0; i < arr.length; i++) {
                                const f = arr.get(i);
                                if (f.id === fieldId) {
                                    arr.delete(i, 1);
                                    arr.insert(i, [{ ...f, image: result.imageUrl }]);
                                    break;
                                }
                            }
                        });
                    }
                }
            } catch (err) {
                console.error("Failed to upload image to field:", err);
            }
        },
        [noteId, uploadToField, getFieldsArray, provider]
    );

    const requestDeleteField = useCallback((field: NoteField) => {
        setPendingDeleteField(field);
    }, []);

    const handleConfirmDelete = useCallback(async () => {
        if (!pendingDeleteField) return;
        const fieldId = pendingDeleteField.id;
        setPendingDeleteField(null);
        try {
            await deleteField(fieldId);
            const arr = getFieldsArray();
            if (arr) {
                for (let i = 0; i < arr.length; i++) {
                    if (arr.get(i).id === fieldId) {
                        arr.delete(i, 1);
                        break;
                    }
                }
            }
        } catch (err) {
            console.error("Failed to delete field:", err);
        }
    }, [pendingDeleteField, deleteField, getFieldsArray]);

    const handleCancelDelete = useCallback(() => {
        setPendingDeleteField(null);
    }, []);

    const handleDragEnd = useCallback(
        async (event: DragEndEvent) => {
            const { active, over } = event;
            if (!over || active.id === over.id) return;

            const oldIndex = fields.findIndex((f) => f.id === active.id);
            const newIndex = fields.findIndex((f) => f.id === over.id);
            if (oldIndex === -1 || newIndex === -1) return;

            const newFields = arrayMove(fields, oldIndex, newIndex);

            const updates = newFields.map((field, index) => ({
                id: field.id,
                position: index * 1000,
                noteId,
            }));

            // Update Yjs (which triggers observeDeep → setFields)
            const arr = getFieldsArray();
            if (arr) {
                provider.document.transact(() => {
                    arr.delete(0, arr.length);
                    const reordered = newFields.map((f, i) => ({ ...f, position: i * 1000 }));
                    arr.push(reordered);
                });
            }

            try {
                await reorderFields(updates);
            } catch (err) {
                console.error("Failed to reorder fields:", err);
            }
        },
        [fields, noteId, reorderFields, getFieldsArray, provider]
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
                            onUploadImage={handleUploadToField}
                            uploadingFieldId={uploadingFieldId}
                        />
                    ))}
                </SortableContext>
            </DndContext>

            {fields.length === 0 && connected && (
                <div className="p-4 text-center text-muted" style={{ fontSize: "14px" }}>
                    No fields yet. Add a text field or image above to get started.
                </div>
            )}

            <DeleteConfirmModal
                isOpen={pendingDeleteField !== null}
                itemType={pendingDeleteField?.fieldType as "rich_text" | "image" | null}
                onClose={handleCancelDelete}
                onConfirm={handleConfirmDelete}
            />
        </div>
    );
}
