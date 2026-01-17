import { useSortable } from "@dnd-kit/sortable";
import TreeItem from "./TreeItem";
import { NoteTreeNode, DropPosition, DragState } from "./types";

interface SortableTreeItemProps {
    item: NoteTreeNode;
    depth: number;
    selectedId: number | null;
    onSelect: (id: number | null) => void;
    onDelete: (id: number) => void;
    onRename: (id: number, title: string) => void;
    onCreateChild: (parentId: number, type: "note" | "folder") => void;
    dragState: DragState;
}

export default function SortableTreeItem({
    item,
    depth,
    selectedId,
    onSelect,
    onDelete,
    onRename,
    onCreateChild,
    dragState,
}: SortableTreeItemProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        isDragging,
    } = useSortable({ id: item.id });

    // For tree structures with DragOverlay, don't apply transforms
    // The DragOverlay handles the visual preview; items stay in place
    const style = {
        opacity: isDragging ? 0 : 1,
    };

    // Determine if this item is the current drop target
    const isDropTarget = dragState.overId === item.id;
    const dropPosition: DropPosition | null = isDropTarget
        ? dragState.dropPosition
        : null;

    // Recursive renderer for children that also uses SortableTreeItem
    const renderChildren = (children: NoteTreeNode[], childDepth: number) => {
        return children.map((child) => (
            <SortableTreeItem
                key={child.id}
                item={child}
                depth={childDepth}
                selectedId={selectedId}
                onSelect={onSelect}
                onDelete={onDelete}
                onRename={onRename}
                onCreateChild={onCreateChild}
                dragState={dragState}
            />
        ));
    };

    return (
        <div ref={setNodeRef} style={style}>
            <TreeItem
                item={item}
                depth={depth}
                selectedId={selectedId}
                onSelect={onSelect}
                onDelete={onDelete}
                onRename={onRename}
                onCreateChild={onCreateChild}
                isDragging={isDragging}
                dropPosition={dropPosition}
                dragHandleProps={listeners}
                dragAttributes={attributes}
                renderChildren={renderChildren}
            />
        </div>
    );
}
