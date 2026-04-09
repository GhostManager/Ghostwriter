import { useState, useMemo, useCallback } from "react";
import {
    DndContext,
    DragOverlay,
    pointerWithin,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    useDroppable,
} from "@dnd-kit/core";
import {
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useNoteMutations } from "./hooks/useNoteMutations";
import { useTreeDnd } from "./hooks/useTreeDnd";
import { useTreeSync } from "./hooks/useTreeSync";
import SortableTreeItem from "./SortableTreeItem";
import TreeItem from "./TreeItem";
import CreateModal from "./CreateModal";
import DeleteConfirmModal from "./DeleteConfirmModal";
import type { NoteTreeNode, FlatNote } from "./types";
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
    const {
        tree,
        flatNodes,
        loading,
        addNode,
        removeNodes,
        updateNode,
    } = useTreeSync({ projectId });

    const { createNote, createFolder, deleteNote, renameNote, moveNote } =
        useNoteMutations();

    const [showCreateModal, setShowCreateModal] = useState(false);
    const [createType, setCreateType] = useState<"note" | "folder">("note");
    const [createParentId, setCreateParentId] = useState<number | null>(null);
    const [pendingDeleteItem, setPendingDeleteItem] = useState<NoteTreeNode | null>(null);

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: { distance: 8 },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    /** Called after any tree mutation to sync Yjs state */
    const onTreeMutated = useCallback(() => {
        // Tree changes propagate through Yjs automatically via addNode/removeNodes/updateNode
    }, []);

    const {
        dragState,
        handleDragStart,
        handleDragOver,
        handleDragEnd: rawDragEnd,
        handleDragCancel,
        calculateNewPosition,
    } = useTreeDnd({ flatNodes, moveNote, onTreeMutated });

    // Wrap handleDragEnd to also update Yjs tree with both parent and position
    const handleDragEnd = useCallback(
        async (event: any) => {
            const { active, over } = event;
            const { overId, dropPosition } = dragState;

            if (over && overId !== null && dropPosition !== null) {
                const activeId = active.id as number;

                if (overId === "tree-top" || overId === "tree-bottom") {
                    const rootNodes = flatNodes
                        .filter((n) => n.parentId === null)
                        .sort((a, b) => a.position - b.position);
                    const newPosition = overId === "tree-top"
                        ? (rootNodes.length > 0 ? rootNodes[0].position - 1000 : 0)
                        : (rootNodes.length > 0 ? rootNodes[rootNodes.length - 1].position + 1000 : 0);
                    updateNode(activeId, { parentId: null, position: newPosition });
                } else {
                    const overNode = flatNodes.find((n) => n.id === overId);
                    if (overNode) {
                        const newParentId = dropPosition === "inside" ? (overId as number) : overNode.parentId;
                        const newPosition = calculateNewPosition(overId as number, dropPosition, newParentId);
                        updateNode(activeId, { parentId: newParentId, position: newPosition });
                    }
                }
            }

            await rawDragEnd(event);
        },
        [dragState, flatNodes, rawDragEnd, updateNode, calculateNewPosition]
    );

    const allItemIds = useMemo(() => flatNodes.map((n) => n.id), [flatNodes]);

    const activeItem = useMemo(() => {
        if (!dragState.activeId) return null;
        const findItem = (nodes: NoteTreeNode[]): NoteTreeNode | null => {
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
        let newId: number;
        if (createType === "folder") {
            newId = await createFolder(projectId, createParentId, title);
        } else {
            newId = await createNote(projectId, createParentId, title);
            onSelect(newId);
        }

        // Add node to Yjs tree for real-time sync
        const position = flatNodes
            .filter((n) => n.parentId === createParentId)
            .reduce((max, n) => Math.max(max, n.position), -1000) + 1000;

        addNode({
            id: newId,
            title,
            nodeType: createType,
            parentId: createParentId,
            position,
        });

        setShowCreateModal(false);
    };

    const requestDelete = (item: NoteTreeNode) => {
        setPendingDeleteItem(item);
    };

    const handleConfirmDelete = async () => {
        if (!pendingDeleteItem) return;
        const id = pendingDeleteItem.id;
        setPendingDeleteItem(null);
        if (selectedId === id) onSelect(null);

        // Collect all descendant IDs
        const idsToRemove = new Set<number>();
        const collectIds = (nodes: NoteTreeNode[]) => {
            for (const node of nodes) {
                idsToRemove.add(node.id);
                collectIds(node.children);
            }
        };
        const findNode = (nodes: NoteTreeNode[]): NoteTreeNode | null => {
            for (const n of nodes) {
                if (n.id === id) return n;
                const found = findNode(n.children);
                if (found) return found;
            }
            return null;
        };
        const targetNode = findNode(tree);
        if (targetNode) collectIds([targetNode]);
        else idsToRemove.add(id);

        await deleteNote(id);
        removeNodes(idsToRemove);
    };

    const handleCancelDelete = () => {
        setPendingDeleteItem(null);
    };

    const handleRename = async (id: number, title: string) => {
        await renameNote(id, title);
        updateNode(id, { title });
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
            <div className="d-flex align-items-center justify-content-center p-3">
                <div className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></div>
                <span>Loading notes...</span>
            </div>
        );
    }

    return (
        <div className="note-tree">
            <div className="p-2 border-bottom d-flex gap-2">
                <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => openCreateModal("note")}
                    title="New Note"
                >
                    <i className="fas fa-plus me-1"></i>Note
                </button>
                <button
                    className="btn btn-sm btn-outline-secondary"
                    onClick={() => openCreateModal("folder")}
                    title="New Folder"
                >
                    <i className="fas fa-folder-plus me-1"></i>Folder
                </button>
                <button
                    className="btn btn-sm btn-outline-secondary ms-auto"
                    onClick={() =>
                        (window.location.href = `/rolodex/ajax/project/${projectId}/notes/export`)
                    }
                    title="Download all notes as ZIP"
                >
                    <i className="fas fa-download"></i>
                </button>
            </div>

            <DndContext
                sensors={sensors}
                collisionDetection={pointerWithin}
                onDragStart={handleDragStart}
                onDragMove={handleDragOver}
                onDragOver={handleDragOver}
                onDragEnd={handleDragEnd}
                onDragCancel={handleDragCancel}
            >
                <div className="tree-items" style={{ overflowY: "auto" }}>
                    <TreeDropSentinel id="tree-top" />
                    <SortableContext
                        items={allItemIds}
                        strategy={verticalListSortingStrategy}
                    >
                        <div className="p-2">
                            {tree.map((item) => (
                                <SortableTreeItem
                                    key={item.id}
                                    item={item}
                                    depth={0}
                                    selectedId={selectedId}
                                    onSelect={onSelect}
                                    onRequestDelete={requestDelete}
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
                    <TreeDropSentinel id="tree-bottom" />
                </div>

                <DragOverlay>
                    {activeItem && (
                        <div className="tree-drag-overlay">
                            <TreeItem
                                item={activeItem}
                                depth={0}
                                selectedId={null}
                                onSelect={() => {}}
                                onRequestDelete={() => {}}
                                onRename={() => {}}
                                onCreateChild={() => {}}
                            />
                        </div>
                    )}
                </DragOverlay>
            </DndContext>

            <CreateModal
                isOpen={showCreateModal}
                type={createType}
                onClose={() => setShowCreateModal(false)}
                onCreate={handleCreate}
            />

            <DeleteConfirmModal
                isOpen={pendingDeleteItem !== null}
                itemType={pendingDeleteItem?.nodeType as "note" | "folder" | null}
                itemTitle={pendingDeleteItem?.title}
                onClose={handleCancelDelete}
                onConfirm={handleConfirmDelete}
            />
        </div>
    );
}

function TreeDropSentinel({ id }: { id: string }) {
    const { setNodeRef, isOver } = useDroppable({ id });
    return (
        <div
            ref={setNodeRef}
            style={{
                minHeight: "24px",
                backgroundColor: isOver ? "rgba(13, 110, 253, 0.15)" : "transparent",
                borderTop: isOver ? "3px solid #0d6efd" : "3px solid transparent",
                transition: "all 0.15s ease",
            }}
        />
    );
}
