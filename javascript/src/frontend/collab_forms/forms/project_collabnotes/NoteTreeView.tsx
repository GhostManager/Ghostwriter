import { useState, useMemo } from "react";
import {
    DndContext,
    DragOverlay,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
} from "@dnd-kit/core";
import {
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useNoteTree } from "./hooks/useNoteTree";
import { useNoteMutations } from "./hooks/useNoteMutations";
import { useTreeDnd } from "./hooks/useTreeDnd";
import SortableTreeItem from "./SortableTreeItem";
import TreeItem from "./TreeItem";
import CreateModal from "./CreateModal";
import "./tree.css";

interface NoteTreeViewProps {
    projectId: number;
    selectedId: number | null;
    onSelect: (id: number | null) => void;
}

export default function NoteTreeView({
    projectId,
    selectedId,
    onSelect,
}: NoteTreeViewProps) {
    const { tree, flatNodes, loading, error, refetch } = useNoteTree(projectId);
    const { createNote, createFolder, deleteNote, renameNote, moveNote } =
        useNoteMutations();

    const [showCreateModal, setShowCreateModal] = useState(false);
    const [createType, setCreateType] = useState<"note" | "folder">("note");
    const [createParentId, setCreateParentId] = useState<number | null>(null);

    // DnD setup
    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8, // Prevent accidental drags
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const {
        dragState,
        handleDragStart,
        handleDragOver,
        handleDragEnd,
        handleDragCancel,
    } = useTreeDnd({ flatNodes, moveNote, refetch });

    // Get all item IDs for SortableContext (flat list of all IDs)
    const allItemIds = useMemo(() => flatNodes.map((n) => n.id), [flatNodes]);

    // Find the currently dragged item for the drag overlay
    const activeItem = useMemo(() => {
        if (!dragState.activeId) return null;
        const findItem = (nodes: typeof tree): typeof tree[0] | null => {
            for (const node of nodes) {
                if (node.id === dragState.activeId) return node;
                if (node.children.length > 0) {
                    const found = findItem(node.children);
                    if (found) return found;
                }
            }
            return null;
        };
        return findItem(tree);
    }, [dragState.activeId, tree]);

    const handleCreate = async (title: string) => {
        if (createType === "folder") {
            await createFolder(projectId, createParentId, title);
        } else {
            const newId = await createNote(projectId, createParentId, title);
            // Select the newly created note
            onSelect(newId);
        }
        await refetch();
        setShowCreateModal(false);
    };

    const handleDelete = async (id: number) => {
        if (selectedId === id) {
            onSelect(null);
        }
        await deleteNote(id);
        await refetch();
    };

    const handleRename = async (id: number, title: string) => {
        await renameNote(id, title);
        await refetch();
    };

    const handleCreateChild = (parentId: number, type: "note" | "folder") => {
        setCreateType(type);
        setCreateParentId(parentId);
        setShowCreateModal(true);
    };

    const openCreateModal = (type: "note" | "folder") => {
        setCreateType(type);
        setCreateParentId(null);
        setShowCreateModal(true);
    };

    if (loading) {
        return (
            <div className="p-3 text-center">
                <div className="spinner-border spinner-border-sm" role="status">
                    <span className="visually-hidden">Loading...</span>
                </div>
                <span className="ms-2">Loading notes...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-3">
                <div className="alert alert-danger" role="alert">
                    {error}
                </div>
                <button className="btn btn-sm btn-primary" onClick={refetch}>
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="note-tree">
            {/* Toolbar */}
            <div className="p-2 border-bottom d-flex gap-2">
                <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => openCreateModal("note")}
                    title="New Note"
                >
                    <i className="fas fa-plus me-1"></i>
                    Note
                </button>
                <button
                    className="btn btn-sm btn-outline-secondary"
                    onClick={() => openCreateModal("folder")}
                    title="New Folder"
                >
                    <i className="fas fa-folder-plus me-1"></i>
                    Folder
                </button>
            </div>

            {/* Tree Items with DnD */}
            <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDragEnd={handleDragEnd}
                onDragCancel={handleDragCancel}
            >
                <SortableContext
                    items={allItemIds}
                    strategy={verticalListSortingStrategy}
                >
                    <div className="tree-items p-2" style={{ overflowY: "auto" }}>
                        {tree.map((item) => (
                            <SortableTreeItem
                                key={item.id}
                                item={item}
                                depth={0}
                                selectedId={selectedId}
                                onSelect={onSelect}
                                onDelete={handleDelete}
                                onRename={handleRename}
                                onCreateChild={handleCreateChild}
                                dragState={dragState}
                            />
                        ))}
                        {tree.length === 0 && (
                            <div className="text-muted small p-2">
                                No notes yet. Create one using the buttons above.
                            </div>
                        )}
                    </div>
                </SortableContext>

                {/* Drag Overlay - shows preview of dragged item */}
                <DragOverlay>
                    {activeItem && (
                        <div className="tree-drag-overlay">
                            <TreeItem
                                item={activeItem}
                                depth={0}
                                selectedId={null}
                                onSelect={() => {}}
                                onDelete={() => {}}
                                onRename={() => {}}
                                onCreateChild={() => {}}
                            />
                        </div>
                    )}
                </DragOverlay>
            </DndContext>

            {/* Create Modal */}
            <CreateModal
                isOpen={showCreateModal}
                type={createType}
                onClose={() => setShowCreateModal(false)}
                onCreate={handleCreate}
            />
        </div>
    );
}
