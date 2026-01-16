export interface NoteTreeNode {
    id: number;
    title: string;
    nodeType: "folder" | "note";
    parentId: number | null;
    position: number;
    children: NoteTreeNode[];
}

export interface FlatNote {
    id: number;
    title: string;
    nodeType: "folder" | "note";
    parentId: number | null;
    position: number;
}

export type DropPosition = "before" | "after" | "inside";

export interface DragState {
    activeId: number | null;
    overId: number | null;
    dropPosition: DropPosition | null;
}
