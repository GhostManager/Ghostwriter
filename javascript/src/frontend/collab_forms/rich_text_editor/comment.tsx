import { faComment } from "@fortawesome/free-solid-svg-icons/faComment";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Editor } from "@tiptap/core";
import { useEditorState } from "@tiptap/react";
import { useEffect, useId, useRef, useState } from "react";
import ReactModal from "react-modal";
import { type CommentEntry } from "../../../tiptap_gw/comment";

function getCurrentUsername(): string {
    return (
        document.getElementById("yjs-username")?.textContent?.trim() ??
        "Unknown"
    );
}

function formatTimestamp(iso: string): string {
    try {
        return new Date(iso).toLocaleString();
    } catch {
        return iso;
    }
}

interface CommentCardProps {
    entry: CommentEntry;
    currentUser: string;
    onEdit: (updated: string) => void;
    onDelete: () => void;
}

function CommentCard({
    entry,
    currentUser,
    onEdit,
    onDelete,
}: CommentCardProps) {
    const [editing, setEditing] = useState(false);
    const [editText, setEditText] = useState(entry.comment);
    const isOwn = entry.author === currentUser;
    const fieldId = useId();

    return (
        <div
            className={`gw-comment-card ${isOwn ? "gw-comment-card-own" : ""}`}
        >
            <div className="gw-comment-card-header">
                <img
                    className="gw-comment-avatar"
                    src={`/users/${encodeURIComponent(entry.author)}/avatar`}
                    alt={`${entry.author} avatar`}
                    onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.display =
                            "none";
                    }}
                />
                <div className="gw-comment-meta">
                    <strong>{entry.author}</strong>
                    <small className="text-muted">
                        {formatTimestamp(entry.timestamp)}
                    </small>
                </div>
                {isOwn && !editing && (
                    <div className="gw-comment-actions">
                        <button
                            type="button"
                            className="btn btn-sm btn-outline-secondary"
                            onClick={() => {
                                setEditText(entry.comment);
                                setEditing(true);
                            }}
                        >
                            Edit
                        </button>
                        <button
                            type="button"
                            className="btn btn-sm btn-outline-danger"
                            onClick={onDelete}
                        >
                            Delete
                        </button>
                    </div>
                )}
            </div>
            {editing ? (
                <div className="gw-comment-edit-form">
                    <label htmlFor={fieldId} className="visually-hidden">
                        Edit comment
                    </label>
                    <textarea
                        id={fieldId}
                        className="form-control form-control-sm"
                        rows={3}
                        value={editText}
                        autoFocus
                        onChange={(e) => setEditText(e.target.value)}
                    />
                    <div className="gw-comment-edit-buttons">
                        <button
                            type="button"
                            className="btn btn-sm btn-primary"
                            disabled={!editText.trim()}
                            onClick={() => {
                                onEdit(editText.trim());
                                setEditing(false);
                            }}
                        >
                            Save
                        </button>
                        <button
                            type="button"
                            className="btn btn-sm btn-secondary"
                            onClick={() => setEditing(false)}
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            ) : (
                <p className="gw-comment-text">{entry.comment}</p>
            )}
        </div>
    );
}

export default function CommentButton({ editor }: { editor: Editor }) {
    const [modalOpen, setModalOpen] = useState(false);
    const [comments, setComments] = useState<CommentEntry[]>([]);
    const [resolved, setResolved] = useState(false);
    const [newComment, setNewComment] = useState("");
    const newCommentId = useId();

    // Saved when the modal opens so commands always target the correct span
    const savedRange = useRef<{ from: number; to: number } | null>(null);

    // Open the modal when the user clicks directly on commented text
    useEffect(() => {
        const dom = editor.view.dom;
        function handleClick(e: MouseEvent) {
            if (!(e.target as HTMLElement).closest(".gw-comment")) return;
            // rAF lets ProseMirror update the selection before we read it
            requestAnimationFrame(() => {
                if (!editor.isActive("gwComment")) return;
                editor.chain().focus().extendMarkRange("gwComment").run();
                const { from, to } = editor.state.selection;
                savedRange.current = { from, to };
                const attrs = editor.getAttributes("gwComment");
                setComments((attrs.comments as CommentEntry[]) ?? []);
                setResolved((attrs.resolved as boolean) ?? false);
                setNewComment("");
                setModalOpen(true);
            });
        }
        dom.addEventListener("click", handleClick);
        return () => dom.removeEventListener("click", handleClick);
    }, [editor]);

    const { enabled, active } = useEditorState({
        editor,
        selector: ({ editor }) => {
            if (!editor.isInitialized) return { enabled: false, active: false };
            const active = editor.isActive("gwComment");
            const { from, to } = editor.state.selection;
            return { enabled: active || from !== to, active };
        },
    });

    // Apply or remove the gwComment mark directly via ProseMirror transaction
    function applyComment(entries: CommentEntry[], res: boolean) {
        const range = savedRange.current;
        if (!range) return;
        const { from, to } = range;
        const markType = editor.schema.marks["gwComment"];
        if (!markType) return;
        const tr = editor.state.tr;
        tr.removeMark(from, to, markType);
        if (entries.length > 0) {
            tr.addMark(
                from,
                to,
                markType.create({ comments: entries, resolved: res })
            );
        }
        editor.view.dispatch(tr);
    }

    function openModal() {
        if (editor.isActive("gwComment")) {
            editor.chain().focus().extendMarkRange("gwComment").run();
            const { from, to } = editor.state.selection;
            savedRange.current = { from, to };
            const attrs = editor.getAttributes("gwComment");
            setComments((attrs.comments as CommentEntry[]) ?? []);
            setResolved((attrs.resolved as boolean) ?? false);
        } else {
            const { from, to } = editor.state.selection;
            savedRange.current = { from, to };
            setComments([]);
            setResolved(false);
        }
        setNewComment("");
        setModalOpen(true);
    }

    function buildUpdated(): CommentEntry[] {
        const currentUser = getCurrentUsername();
        if (!newComment.trim()) return [...comments];
        return [
            ...comments,
            {
                author: currentUser,
                comment: newComment.trim(),
                timestamp: new Date().toISOString(),
            },
        ];
    }

    function handleSave() {
        applyComment(buildUpdated(), resolved);
        setModalOpen(false);
    }

    function handleResolveToggle() {
        const updated = buildUpdated();
        if (updated.length > 0) applyComment(updated, !resolved);
        setModalOpen(false);
    }

    function handleRemoveAll() {
        applyComment([], false);
        setModalOpen(false);
    }

    function handleEditComment(index: number, updatedText: string) {
        setComments((prev) =>
            prev.map((c, i) =>
                i === index
                    ? {
                          ...c,
                          comment: updatedText,
                          timestamp: new Date().toISOString(),
                      }
                    : c
            )
        );
    }

    function handleDeleteComment(index: number) {
        setComments((prev) => prev.filter((_, i) => i !== index));
    }

    const currentUser = getCurrentUsername();
    const hasExistingComments = comments.length > 0;

    return (
        <>
            <button
                tabIndex={-1}
                title="Comment"
                type="button"
                disabled={!enabled}
                className={active ? "is-active" : undefined}
                onClick={(e) => {
                    e.preventDefault();
                    openModal();
                }}
            >
                <FontAwesomeIcon icon={faComment} />
            </button>
            <ReactModal
                isOpen={modalOpen}
                onRequestClose={() => setModalOpen(false)}
                contentLabel="Comments"
                className="modal-dialog modal-dialog-centered"
            >
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title">
                            {hasExistingComments ? "Comments" : "Add Comment"}
                        </h5>
                        {resolved && (
                            <span className="badge bg-success ms-2">
                                Resolved
                            </span>
                        )}
                    </div>
                    <form
                        className="modal-body"
                        onSubmit={(ev) => {
                            ev.preventDefault();
                            handleSave();
                        }}
                    >
                        {hasExistingComments && (
                            <div className="gw-comment-list mb-3">
                                {comments.map((entry, i) => (
                                    <CommentCard
                                        key={i}
                                        entry={entry}
                                        currentUser={currentUser}
                                        onEdit={(text) =>
                                            handleEditComment(i, text)
                                        }
                                        onDelete={() => handleDeleteComment(i)}
                                    />
                                ))}
                            </div>
                        )}
                        <div className="form-group">
                            <label htmlFor={newCommentId}>
                                {hasExistingComments
                                    ? "Add a reply"
                                    : "Comment"}
                            </label>
                            <textarea
                                id={newCommentId}
                                className="form-control"
                                rows={3}
                                value={newComment}
                                autoFocus={!hasExistingComments}
                                placeholder={
                                    hasExistingComments
                                        ? "Write a reply..."
                                        : "Write a comment..."
                                }
                                onChange={(e) => setNewComment(e.target.value)}
                            />
                        </div>
                    </form>
                    <div className="modal-footer flex-wrap gap-2">
                        <button
                            type="button"
                            className="btn btn-primary"
                            disabled={
                                !newComment.trim() && comments.length === 0
                            }
                            onClick={handleSave}
                        >
                            Save
                        </button>
                        {hasExistingComments && (
                            <>
                                <button
                                    type="button"
                                    className={`btn ${
                                        resolved ? "btn-warning" : "btn-success"
                                    }`}
                                    onClick={handleResolveToggle}
                                >
                                    {resolved ? "Unresolve" : "Resolve"}
                                </button>
                                <button
                                    type="button"
                                    className="btn btn-danger"
                                    onClick={handleRemoveAll}
                                >
                                    Remove All
                                </button>
                            </>
                        )}
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => setModalOpen(false)}
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            </ReactModal>
        </>
    );
}
