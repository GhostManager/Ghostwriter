import { useState, useCallback } from "react";
import { DragEndEvent, DragOverEvent, DragStartEvent } from "@dnd-kit/core";
import { FlatNote, DropPosition, DragState } from "../types";

interface UseTreeDndProps {
    flatNodes: FlatNote[];
    moveNote: (id: number, parentId: number | null, position: number) => Promise<void>;
    refetch: () => Promise<void>;
}

export function useTreeDnd({ flatNodes, moveNote, refetch }: UseTreeDndProps) {
    const [dragState, setDragState] = useState<DragState>({
        activeId: null,
        overId: null,
        dropPosition: null,
    });

    // Check if nodeId is a descendant of ancestorId
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

    // Check if drop is valid (cannot drop into self or descendants)
    const isValidDrop = useCallback(
        (activeId: number, overId: number, dropPosition: DropPosition): boolean => {
            if (activeId === overId) return false;
            const activeNode = flatNodes.find((n) => n.id === activeId);
            if (!activeNode) return false;

            // If dropping into a folder, check it's not a descendant
            if (dropPosition === "inside") {
                const overNode = flatNodes.find((n) => n.id === overId);
                if (!overNode || overNode.nodeType !== "folder") return false;
                if (isDescendant(overId, activeId)) return false;
            }

            return true;
        },
        [flatNodes, isDescendant]
    );

    // Calculate new position for the dropped item (must return integer)
    const calculateNewPosition = useCallback(
        (
            overId: number,
            dropPosition: DropPosition,
            newParentId: number | null
        ): number => {
            // Get siblings in the target parent
            const siblings = flatNodes
                .filter((n) => n.parentId === newParentId)
                .sort((a, b) => a.position - b.position);

            if (siblings.length === 0) {
                return 0;
            }

            const overIndex = siblings.findIndex((n) => n.id === overId);

            if (dropPosition === "inside") {
                // Dropping into a folder - get max position of children
                const children = flatNodes
                    .filter((n) => n.parentId === overId)
                    .sort((a, b) => a.position - b.position);
                if (children.length === 0) return 0;
                return children[children.length - 1].position + 1000;
            }

            if (dropPosition === "before") {
                if (overIndex === 0) {
                    // Before first item
                    return siblings[0].position - 1000;
                }
                // Between previous and current - use midpoint rounded
                const prevPos = siblings[overIndex - 1].position;
                const currPos = siblings[overIndex].position;
                return Math.floor((prevPos + currPos) / 2);
            }

            // dropPosition === "after"
            if (overIndex === siblings.length - 1) {
                // After last item
                return siblings[overIndex].position + 1000;
            }
            // Between current and next - use midpoint rounded
            const currPos = siblings[overIndex].position;
            const nextPos = siblings[overIndex + 1].position;
            return Math.floor((currPos + nextPos) / 2);
        },
        [flatNodes]
    );

    const handleDragStart = useCallback((event: DragStartEvent) => {
        setDragState({
            activeId: event.active.id as number,
            overId: null,
            dropPosition: null,
        });
    }, []);

    const handleDragOver = useCallback(
        (event: DragOverEvent) => {
            const { active, over } = event;
            if (!over) {
                setDragState((prev) => ({
                    ...prev,
                    overId: null,
                    dropPosition: null,
                }));
                return;
            }

            const overId = over.id as number;
            const activeId = active.id as number;

            // Skip if same item
            if (activeId === overId) {
                setDragState((prev) => ({
                    ...prev,
                    overId: null,
                    dropPosition: null,
                }));
                return;
            }

            const overNode = flatNodes.find((n) => n.id === overId);
            let dropPosition: DropPosition;

            // For folders, default to "inside"; for notes, default to "after"
            if (overNode?.nodeType === "folder") {
                dropPosition = "inside";
            } else {
                dropPosition = "after";
            }

            // Check if valid
            if (!isValidDrop(activeId, overId, dropPosition)) {
                // If "inside" is not valid, try "after"
                if (dropPosition === "inside") {
                    dropPosition = "after";
                    if (!isValidDrop(activeId, overId, dropPosition)) {
                        setDragState((prev) => ({
                            ...prev,
                            overId: null,
                            dropPosition: null,
                        }));
                        return;
                    }
                } else {
                    setDragState((prev) => ({
                        ...prev,
                        overId: null,
                        dropPosition: null,
                    }));
                    return;
                }
            }

            setDragState((prev) => ({
                ...prev,
                overId,
                dropPosition,
            }));
        },
        [flatNodes, isValidDrop]
    );

    const handleDragEnd = useCallback(
        async (event: DragEndEvent) => {
            const { active, over } = event;
            const { overId, dropPosition } = dragState;

            // Reset drag state
            setDragState({
                activeId: null,
                overId: null,
                dropPosition: null,
            });

            if (!over || overId === null || dropPosition === null) return;

            const activeId = active.id as number;
            const overNode = flatNodes.find((n) => n.id === overId);
            if (!overNode) return;

            // Determine new parent
            let newParentId: number | null;
            if (dropPosition === "inside") {
                newParentId = overId;
            } else {
                newParentId = overNode.parentId;
            }

            // Calculate new position
            const newPosition = calculateNewPosition(overId, dropPosition, newParentId);

            // Perform the move
            try {
                await moveNote(activeId, newParentId, newPosition);
                await refetch();
            } catch (error) {
                console.error("Failed to move note:", error);
            }
        },
        [dragState, flatNodes, calculateNewPosition, moveNote, refetch]
    );

    const handleDragCancel = useCallback(() => {
        setDragState({
            activeId: null,
            overId: null,
            dropPosition: null,
        });
    }, []);

    return {
        dragState,
        handleDragStart,
        handleDragOver,
        handleDragEnd,
        handleDragCancel,
    };
}
