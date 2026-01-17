import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import RichTextEditor from "../../rich_text_editor";
import ImageField from "./ImageField";
import type { NoteField } from "./types";
import type { HocuspocusProvider } from "@hocuspocus/provider";

interface NoteFieldEditorProps {
    field: NoteField;
    provider: HocuspocusProvider;
    connected: boolean;
    onDelete: () => void;
}

export default function NoteFieldEditor({
    field,
    provider,
    connected,
    onDelete,
}: NoteFieldEditorProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({
        id: field.id,
        data: {
            type: "field",
            field,
        },
    });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className="note-field-wrapper"
        >
            <div className="note-field-header" style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                <button
                    {...attributes}
                    {...listeners}
                    className="btn btn-sm btn-secondary"
                    title="Drag to reorder"
                    style={{ cursor: "grab", padding: "4px 8px" }}
                >
                    <i className="fas fa-grip-vertical"></i>
                </button>
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        onDelete();
                    }}
                    className="btn btn-sm btn-danger"
                    title="Delete field"
                    style={{ padding: "4px 8px" }}
                >
                    <i className="fas fa-trash"></i>
                </button>
                <span style={{ fontSize: "12px", color: "#666" }}>
                    {field.fieldType === "rich_text" ? "Text" : "Image"}
                </span>
            </div>

            {field.fieldType === "rich_text" ? (
                <div className="form-group">
                    <RichTextEditor
                        connected={connected}
                        provider={provider}
                        fragment={provider.document.getXmlFragment(`field_${field.id}`)}
                    />
                </div>
            ) : field.image ? (
                <ImageField
                    imageUrl={field.image}
                    onDelete={onDelete}
                />
            ) : null}
        </div>
    );
}
