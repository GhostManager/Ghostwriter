import { useState, useCallback, useRef } from "react";
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
    const lastOverId = useRef<number | null>(null);

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
        lastOverId.current = null;
        setDragState({ activeId: event.active.id as number, overId: null, dropPosition: null });
    }, []);

    const handleDragOver = useCallback(
        (event: DragOverEvent) => {
            const { active, over } = event;

            if (!over) {
                setDragState((prev) => ({ ...prev, overId: null, dropPosition: null }));
                lastOverId.current = null;
                return;
            }

            const activeId = active.id as number;
            const overIdRaw = over.id;

            // Handle sentinel drop zones at top/bottom of tree
            if (overIdRaw === "tree-top" || overIdRaw === "tree-bottom") {
                const dropPosition: DropPosition = overIdRaw === "tree-top" ? "before" : "after";
                setDragState((prev) => ({ ...prev, overId: overIdRaw as any, dropPosition }));
                return;
            }

            const overId = overIdRaw as number;

            if (activeId === overId) {
                setDragState((prev) => ({ ...prev, overId: null, dropPosition: null }));
                return;
            }

            const overNode = flatNodes.find((n) => n.id === overId);
            if (!overNode) {
                setDragState((prev) => ({ ...prev, overId: null, dropPosition: null }));
                return;
            }

            let dropPosition: DropPosition;
            const movingDown = event.delta.y > 0;

            if (overNode.nodeType === "folder") {
                dropPosition = "inside";
            } else {
                dropPosition = movingDown ? "after" : "before";
            }

            if (!isValidDrop(activeId, overId, dropPosition)) {
                if (dropPosition === "inside") {
                    dropPosition = movingDown ? "after" : "before";
                    if (!isValidDrop(activeId, overId, dropPosition)) {
                        setDragState((prev) => ({ ...prev, overId: null, dropPosition: null }));
                        return;
                    }
                } else {
                    setDragState((prev) => ({ ...prev, overId: null, dropPosition: null }));
                    return;
                }
            }

            lastOverId.current = overId;
            setDragState((prev) => ({ ...prev, overId, dropPosition }));
        },
        [flatNodes, isValidDrop]
    );

    const handleDragEnd = useCallback(
        async (event: DragEndEvent) => {
            const { active, over } = event;
            const { overId, dropPosition } = dragState;

            setDragState({ activeId: null, overId: null, dropPosition: null });
            lastOverId.current = null;

            if (!over || overId === null || dropPosition === null) return;

            const activeId = active.id as number;

            // Handle sentinel drop zones
            let newParentId: number | null;
            let newPosition: number;

            if (overId === "tree-top" || overId === "tree-bottom") {
                const rootNodes = flatNodes
                    .filter((n) => n.parentId === null)
                    .sort((a, b) => a.position - b.position);
                newParentId = null;
                if (overId === "tree-top") {
                    newPosition = rootNodes.length > 0 ? rootNodes[0].position - 1000 : 0;
                } else {
                    newPosition = rootNodes.length > 0 ? rootNodes[rootNodes.length - 1].position + 1000 : 0;
                }
            } else {
                const overNode = flatNodes.find((n) => n.id === overId);
                if (!overNode) return;
                newParentId = dropPosition === "inside" ? (overId as number) : overNode.parentId;
                newPosition = calculateNewPosition(overId as number, dropPosition, newParentId);
            }

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
        lastOverId.current = null;
    }, []);

    return { dragState, handleDragStart, handleDragOver, handleDragEnd, handleDragCancel, calculateNewPosition };
}
