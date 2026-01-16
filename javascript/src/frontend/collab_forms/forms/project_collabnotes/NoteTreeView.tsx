import { useState } from "react";
import { useNoteTree } from "./hooks/useNoteTree";
import { useNoteMutations } from "./hooks/useNoteMutations";
import TreeItem from "./TreeItem";
import CreateModal from "./CreateModal";

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
    const { tree, loading, error, refetch } = useNoteTree(projectId);
    const { createNote, createFolder, deleteNote, renameNote } =
        useNoteMutations();

    const [showCreateModal, setShowCreateModal] = useState(false);
    const [createType, setCreateType] = useState<"note" | "folder">("note");
    const [createParentId, setCreateParentId] = useState<number | null>(null);

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

            {/* Tree Items */}
            <div className="tree-items p-2" style={{ overflowY: "auto" }}>
                {tree.map((item) => (
                    <TreeItem
                        key={item.id}
                        item={item}
                        depth={0}
                        selectedId={selectedId}
                        onSelect={onSelect}
                        onDelete={handleDelete}
                        onRename={handleRename}
                        onCreateChild={handleCreateChild}
                    />
                ))}
                {tree.length === 0 && (
                    <div className="text-muted small p-2">
                        No notes yet. Create one using the buttons above.
                    </div>
                )}
            </div>

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
