import { useState, forwardRef } from "react";
import { NoteTreeNode, DropPosition } from "./types";

interface TreeItemProps {
    item: NoteTreeNode;
    depth: number;
    selectedId: number | null;
    onSelect: (id: number | null) => void;
    onRequestDelete: (item: NoteTreeNode) => void;
    onRename: (id: number, title: string) => void;
    onCreateChild: (parentId: number, type: "note" | "folder") => void;
    // DnD props
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
        if (e.key === "Enter") {
            handleRenameSubmit();
        } else if (e.key === "Escape") {
            setRenameValue(item.title);
            setIsRenaming(false);
        }
    };

    const handleDeleteClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        onRequestDelete(item);
    };

    const handleRenameClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        setRenameValue(item.title);
        setIsRenaming(true);
    };

    const handleAddNote = (e: React.MouseEvent) => {
        e.stopPropagation();
        onCreateChild(item.id, "note");
        setExpanded(true);
    };

    const handleAddFolder = (e: React.MouseEvent) => {
        e.stopPropagation();
        onCreateChild(item.id, "folder");
        setExpanded(true);
    };

    // Build class names for DnD visual states
    const dropClass = dropPosition
        ? `tree-item-drop-${dropPosition}`
        : "";

    return (
        <div
            className={`tree-item-container ${dropClass}`}
            {...dragAttributes}
        >
            <div
                className={`tree-item d-flex align-items-center py-1 ${
                    isSelected ? "bg-primary text-white" : ""
                } ${isDragging ? "tree-item-dragging" : ""}`}
                style={{
                    paddingLeft: `${depth * 20 + 8}px`,
                    paddingRight: "8px",
                    cursor: isDragging ? "grabbing" : "grab",
                    borderRadius: "4px",
                }}
                onClick={handleClick}
                {...dragHandleProps}
            >
                {/* Expand/collapse icon for folders */}
                <span
                    className="me-1"
                    style={{ width: "16px", textAlign: "center" }}
                >
                    {isFolder ? (
                        hasChildren ? (
                            expanded ? (
                                <i className="fas fa-chevron-down fa-xs"></i>
                            ) : (
                                <i className="fas fa-chevron-right fa-xs"></i>
                            )
                        ) : null
                    ) : null}
                </span>

                {/* Icon */}
                <span className="me-2">
                    {isFolder ? (
                        <i
                            className={`fas ${
                                expanded ? "fa-folder-open" : "fa-folder"
                            }`}
                        ></i>
                    ) : (
                        <i className="fas fa-file-alt"></i>
                    )}
                </span>

                {/* Title */}
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
                    <span className="flex-grow-1 text-truncate">
                        {item.title}
                    </span>
                )}

                {/* Actions */}
                {!isRenaming && (
                    <span className="tree-item-actions ms-auto">
                        {isFolder && (
                            <>
                                <button
                                    className="btn btn-link btn-sm p-0 me-1"
                                    onClick={handleAddNote}
                                    title="Add note"
                                >
                                    <i className="fas fa-plus fa-xs"></i>
                                </button>
                                <button
                                    className="btn btn-link btn-sm p-0 me-1"
                                    onClick={handleAddFolder}
                                    title="Add subfolder"
                                >
                                    <i className="fas fa-folder-plus fa-xs"></i>
                                </button>
                            </>
                        )}
                        <button
                            className="btn btn-link btn-sm p-0 me-1"
                            onClick={handleRenameClick}
                            title="Rename"
                        >
                            <i className="fas fa-edit fa-xs"></i>
                        </button>
                        <button
                            className="btn btn-link btn-sm p-0 text-danger"
                            onClick={handleDeleteClick}
                            title="Delete"
                        >
                            <i className="fas fa-trash fa-xs"></i>
                        </button>
                    </span>
                )}
            </div>

            {/* Children */}
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
