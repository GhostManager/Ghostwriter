import { useState } from "react";
import { NoteTreeNode, DropPosition } from "./types";

interface TreeItemProps {
    item: NoteTreeNode;
    depth: number;
    selectedId: number | null;
    onSelect: (id: number | null) => void;
    onRequestDelete: (item: NoteTreeNode) => void;
    onRename: (id: number, title: string) => void;
    onCreateChild: (parentId: number, type: "note" | "folder") => void;
    isDragging?: boolean;
    dropPosition?: DropPosition | null;
    dragHandleProps?: Record<string, unknown>;
    dragAttributes?: Record<string, unknown>;
    renderChildren?: (children: NoteTreeNode[], depth: number) => React.ReactNode;
}

export default function TreeItem({
    item,
    depth,
    selectedId,
    onSelect,
    onRequestDelete,
    onRename,
    onCreateChild,
    isDragging = false,
    dropPosition = null,
    dragHandleProps,
    dragAttributes,
    renderChildren,
}: TreeItemProps) {
    const [expanded, setExpanded] = useState(true);
    const [isRenaming, setIsRenaming] = useState(false);
    const [renameValue, setRenameValue] = useState(item.title);

    const isFolder = item.nodeType === "folder";
    const isSelected = selectedId === item.id;
    const hasChildren = item.children.length > 0;

    const handleClick = () => {
        if (isFolder) {
            setExpanded(!expanded);
        } else {
            onSelect(item.id);
        }
    };

    const handleRenameSubmit = () => {
        if (renameValue.trim() && renameValue !== item.title) {
            onRename(item.id, renameValue.trim());
        }
        setIsRenaming(false);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") handleRenameSubmit();
        else if (e.key === "Escape") {
            setRenameValue(item.title);
            setIsRenaming(false);
        }
    };

    const dropClass = dropPosition ? `tree-item-drop-${dropPosition}` : "";

    // Inline drop indicator styles as fallback (works regardless of CSS loading)
    const dropIndicatorStyle: React.CSSProperties = {};
    if (dropPosition === "before") {
        dropIndicatorStyle.borderTop = "3px solid #0d6efd";
    } else if (dropPosition === "after") {
        dropIndicatorStyle.borderBottom = "3px solid #0d6efd";
    } else if (dropPosition === "inside") {
        dropIndicatorStyle.outline = "2px solid #0d6efd";
        dropIndicatorStyle.outlineOffset = "-2px";
        dropIndicatorStyle.borderRadius = "4px";
        dropIndicatorStyle.backgroundColor = "rgba(13, 110, 253, 0.1)";
    }

    const actionButtonClass = isSelected
        ? "btn btn-sm p-0 me-1 text-white"
        : "btn btn-link btn-sm p-0 me-1";

    const deleteButtonClass = isSelected
        ? "btn btn-sm p-0 text-white"
        : "btn btn-link btn-sm p-0 text-danger";

    return (
        <div className={`tree-item-container ${dropClass}`} style={dropIndicatorStyle} {...dragAttributes}>
            <div
                className={`tree-item d-flex align-items-center py-1 ${
                    isSelected ? "bg-primary text-white" : ""
                } ${isDragging ? "tree-item-dragging" : ""}`}
                style={{
                    paddingLeft: `${depth * 20 + 8}px`,
                    paddingRight: "8px",
                    cursor: isDragging ? "grabbing" : "grab",
                    borderRadius: "4px",
                    overflow: "hidden",
                }}
                onClick={handleClick}
                {...dragHandleProps}
            >
                <span className="me-1" style={{ width: "16px", textAlign: "center" }}>
                    {isFolder && hasChildren && (
                        expanded
                            ? <i className="fas fa-chevron-down fa-xs"></i>
                            : <i className="fas fa-chevron-right fa-xs"></i>
                    )}
                </span>

                <span className="me-2">
                    {isFolder ? (
                        <i className={`fas ${expanded ? "fa-folder-open" : "fa-folder"}`}></i>
                    ) : (
                        <i className="fas fa-file-alt"></i>
                    )}
                </span>

                {isRenaming ? (
                    <input
                        type="text"
                        className="form-control form-control-sm"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={handleRenameSubmit}
                        onKeyDown={handleKeyDown}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                        style={{ maxWidth: "150px" }}
                    />
                ) : (
                    <span className="flex-grow-1 text-truncate" style={{ minWidth: 0 }}>
                        {item.title}
                    </span>
                )}

                {!isRenaming && (
                    <span className="tree-item-actions flex-shrink-0">
                        {isFolder && (
                            <>
                                <button
                                    className={actionButtonClass}
                                    onClick={(e) => { e.stopPropagation(); onCreateChild(item.id, "note"); setExpanded(true); }}
                                    title="Add note"
                                >
                                    <i className="fas fa-plus"></i>
                                </button>
                                <button
                                    className={actionButtonClass}
                                    onClick={(e) => { e.stopPropagation(); onCreateChild(item.id, "folder"); setExpanded(true); }}
                                    title="Add subfolder"
                                >
                                    <i className="fas fa-folder-plus"></i>
                                </button>
                            </>
                        )}
                        <button
                            className={actionButtonClass}
                            onClick={(e) => { e.stopPropagation(); setRenameValue(item.title); setIsRenaming(true); }}
                            title="Rename"
                        >
                            <i className="fas fa-edit"></i>
                        </button>
                        <button
                            className={deleteButtonClass}
                            onClick={(e) => { e.stopPropagation(); onRequestDelete(item); }}
                            title="Delete"
                        >
                            <i className="fas fa-trash"></i>
                        </button>
                    </span>
                )}
            </div>

            {isFolder && expanded && item.children.length > 0 && (
                <div className="tree-children">
                    {renderChildren
                        ? renderChildren(item.children, depth + 1)
                        : item.children.map((child) => (
                              <TreeItem
                                  key={child.id}
                                  item={child}
                                  depth={depth + 1}
                                  selectedId={selectedId}
                                  onSelect={onSelect}
                                  onRequestDelete={onRequestDelete}
                                  onRename={onRename}
                                  onCreateChild={onCreateChild}
                              />
                          ))}
                </div>
            )}
        </div>
    );
}
