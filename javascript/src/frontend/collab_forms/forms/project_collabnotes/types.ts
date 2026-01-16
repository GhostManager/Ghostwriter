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
