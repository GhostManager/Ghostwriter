import { useState, useCallback } from "react";
import { DragEndEvent, DragOverEvent, DragStartEvent } from "@dnd-kit/core";
import { FlatNote, DropPosition, DragState } from "../types";

interface UseTreeDndProps {
    flatNodes: FlatNote[];
    moveNote: (id: number, parentId: number | null, position: number) => Promise<void>;
    onTreeMutated: () => void;
}

export function useTreeDnd({ flatNodes, moveNote, onTreeMutated }: UseTreeDndProps) {
    const [dragState, setDragState] = useState<DragState>({
        activeId: null,
        overId: null,
        dropPosition: null,
    });

    const isDescendant = useCallback(
        (nodeId: number, ancestorId: number): boolean => {
            let current = flatNodes.find((n) => n.id === nodeId);
            while (current?.parentId !== null) {
                if (current.parentId === ancestorId) return true;
                current = flatNodes.find((n) => n.id === current!.parentId);
            }
            return false;
        },
        [flatNodes]
    );

    const isValidDrop = useCallback(
        (activeId: number, overId: number, dropPosition: DropPosition): boolean => {
            if (activeId === overId) return false;
            const activeNode = flatNodes.find((n) => n.id === activeId);
            if (!activeNode) return false;

            if (dropPosition === "inside") {
                const overNode = flatNodes.find((n) => n.id === overId);
                if (!overNode || overNode.nodeType !== "folder") return false;
                if (isDescendant(overId, activeId)) return false;
            }

            return true;
        },
        [flatNodes, isDescendant]
    );

    const calculateNewPosition = useCallback(
        (overId: number, dropPosition: DropPosition, newParentId: number | null): number => {
            const siblings = flatNodes
                .filter((n) => n.parentId === newParentId)
                .sort((a, b) => a.position - b.position);

            if (siblings.length === 0) return 0;

            const overIndex = siblings.findIndex((n) => n.id === overId);

            if (dropPosition === "inside") {
                const children = flatNodes
                    .filter((n) => n.parentId === overId)
                    .sort((a, b) => a.position - b.position);
                if (children.length === 0) return 0;
                return children[children.length - 1].position + 1000;
            }

            if (dropPosition === "before") {
                if (overIndex === 0) return siblings[0].position - 1000;
                const prevPos = siblings[overIndex - 1].position;
                const currPos = siblings[overIndex].position;
                return Math.floor((prevPos + currPos) / 2);
            }

            if (overIndex === siblings.length - 1) return siblings[overIndex].position + 1000;
            const currPos = siblings[overIndex].position;
            const nextPos = siblings[overIndex + 1].position;
            return Math.floor((currPos + nextPos) / 2);
        },
        [flatNodes]
    );

    const handleDragStart = useCallback((event: DragStartEvent) => {
        setDragState({ activeId: event.active.id as number, overId: null, dropPosition: null });
    }, []);

    const handleDragOver = useCallback(
        (event: DragOverEvent) => {
            const { active, over } = event;
            if (!over) {
                setDragState((prev) => ({ ...prev, overId: null, dropPosition: null }));
                return;
            }

            const overId = over.id as number;
            const activeId = active.id as number;

            if (activeId === overId) {
                setDragState((prev) => ({ ...prev, overId: null, dropPosition: null }));
                return;
            }

            const overNode = flatNodes.find((n) => n.id === overId);
            if (!overNode) {
                setDragState((prev) => ({ ...prev, overId: null, dropPosition: null }));
                return;
            }

            // Determine drop position based on dragged item's Y relative to the over item.
            // Use the translated rect of the active (dragged) element to get current position.
            let dropPosition: DropPosition;
            const overRect = over.rect;
            const activeTranslated = active.rect.current.translated;
            const activeCenterY = activeTranslated
                ? activeTranslated.top + activeTranslated.height / 2
                : null;

            if (overNode.nodeType === "folder") {
                // Folders have 3 zones: top 25% = before, middle 50% = inside, bottom 25% = after
                if (activeCenterY !== null && overRect) {
                    const relY = activeCenterY - overRect.top;
                    const height = overRect.height;
                    if (relY < height * 0.25) {
                        dropPosition = "before";
                    } else if (relY > height * 0.75) {
                        dropPosition = "after";
                    } else {
                        dropPosition = "inside";
                    }
                } else {
                    dropPosition = "inside";
                }
            } else {
                // Notes have 2 zones: top 50% = before, bottom 50% = after
                if (activeCenterY !== null && overRect) {
                    const relY = activeCenterY - overRect.top;
                    dropPosition = relY < overRect.height * 0.5 ? "before" : "after";
                } else {
                    dropPosition = "after";
                }
            }

            if (!isValidDrop(activeId, overId, dropPosition)) {
                // Fallback: try "after" if "inside" was invalid
                if (dropPosition === "inside") {
                    dropPosition = "after";
                    if (!isValidDrop(activeId, overId, dropPosition)) {
                        setDragState((prev) => ({ ...prev, overId: null, dropPosition: null }));
                        return;
                    }
                } else {
                    setDragState((prev) => ({ ...prev, overId: null, dropPosition: null }));
                    return;
                }
            }

            setDragState((prev) => ({ ...prev, overId, dropPosition }));
        },
        [flatNodes, isValidDrop]
    );

    const handleDragEnd = useCallback(
        async (event: DragEndEvent) => {
            const { active, over } = event;
            const { overId, dropPosition } = dragState;

            setDragState({ activeId: null, overId: null, dropPosition: null });

            if (!over || overId === null || dropPosition === null) return;

            const activeId = active.id as number;
            const overNode = flatNodes.find((n) => n.id === overId);
            if (!overNode) return;

            const newParentId = dropPosition === "inside" ? overId : overNode.parentId;
            const newPosition = calculateNewPosition(overId, dropPosition, newParentId);

            try {
                await moveNote(activeId, newParentId, newPosition);
                onTreeMutated();
            } catch (error) {
                console.error("Failed to move note:", error);
            }
        },
        [dragState, flatNodes, calculateNewPosition, moveNote, onTreeMutated]
    );

    const handleDragCancel = useCallback(() => {
        setDragState({ activeId: null, overId: null, dropPosition: null });
    }, []);

    return { dragState, handleDragStart, handleDragOver, handleDragEnd, handleDragCancel };
}
