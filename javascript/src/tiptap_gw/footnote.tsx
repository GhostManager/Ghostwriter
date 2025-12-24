import { Node, NodeViewProps } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer, useEditorState } from "@tiptap/react";
import { useRef, useState, useEffect } from "react";
import ReactDOM from "react-dom";

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        footnote: {
            /**
             * Insert a footnote
             * @example editor.commands.insertFootnote({ content: 'Footnote text' })
             */
            insertFootnote: (options: { content: string }) => ReturnType;
            /**
             * Update footnote content
             * @example editor.commands.updateFootnote({ content: 'Updated text' })
             */
            updateFootnote: (options: { content: string }) => ReturnType;
        };
    }
}

type FootnoteOptions = Record<string, never>;

// Simple view component for footnotes in the editor
function FootnoteView({ node, getPos, editor }: NodeViewProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState("");
    const [popoverPosition, setPopoverPosition] = useState({ top: 0, left: 0 });
    const supRef = useRef<HTMLElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Use useEditorState to recalculate footnote number when document changes
    const footnoteNumber = useEditorState({
        editor,
        selector: ({ editor }) => {
            // Calculate footnote number by counting footnotes before this one
            let number = 1;
            if (typeof getPos === "function") {
                const pos = getPos();
                if (pos !== undefined) {
                    editor.state.doc.nodesBetween(0, pos, (n) => {
                        if (n.type.name === "footnote") {
                            number++;
                        }
                    });
                }
            }
            return number;
        },
    });

    // Get footnote content - try textContent first, then attrs.content as fallback
    const footnoteContent = node.textContent || node.attrs.content || "";

    const handleClick = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();

        setEditValue(footnoteContent || "");
        setIsEditing(true);
    };

    // Update popover position when scrolling
    const updatePosition = () => {
        if (supRef.current) {
            const rect = supRef.current.getBoundingClientRect();
            setPopoverPosition({
                top: rect.bottom + 5,
                left: rect.left,
            });
        }
    };

    // Update position when editing starts and on scroll
    useEffect(() => {
        if (isEditing) {
            updatePosition();

            const handleScroll = () => {
                updatePosition();
            };

            window.addEventListener("scroll", handleScroll, true);
            return () => window.removeEventListener("scroll", handleScroll, true);
        }
    }, [isEditing]);

    const handleSave = () => {
        const newValue = editValue.trim();
        const oldValue = (node.textContent || node.attrs.content || "").trim();

        // Only update if the value has actually changed
        if (newValue && newValue !== oldValue) {
            const pos = getPos();
            if (typeof pos === "number") {
                const tr = editor.state.tr;
                const from = pos;
                const to = pos + node.nodeSize;

                // Create new footnote node with updated content
                const newNode = editor.schema.nodes.footnote.create(
                    node.attrs,
                    editor.schema.text(newValue)
                );

                tr.replaceRangeWith(from, to, newNode);
                editor.view.dispatch(tr);
            }
        }
        setIsEditing(false);
    };

    const handleCancel = () => {
        setEditValue(footnoteContent);
        setIsEditing(false);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Escape") {
            e.preventDefault();
            handleCancel();
        } else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            handleSave();
        }
    };

    // Focus input when popover opens
    useEffect(() => {
        if (isEditing && inputRef.current) {
            inputRef.current.focus();
            inputRef.current.select();
        }
    }, [isEditing]);

    // Close popover when clicking outside
    useEffect(() => {
        if (!isEditing) return;

        const handleClickOutside = (e: MouseEvent) => {
            const target = e.target as HTMLElement;
            // Close if clicking outside popover and not on this specific footnote
            if (!target.closest(".footnote-popover") && target !== supRef.current && !supRef.current?.contains(target)) {
                handleSave();
            }
        };

        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [isEditing, editValue]);

    return (
        <NodeViewWrapper as="span" className="footnote-marker">
            <sup
                ref={supRef}
                className="footnote-reference"
                onClick={handleClick}
                title="Click to edit footnote"
                style={{
                    cursor: "pointer",
                    userSelect: "none",
                    color: "#0066cc",
                    fontWeight: "bold",
                }}
            >
                {footnoteNumber}
            </sup>

            {isEditing &&
                ReactDOM.createPortal(
                    <div
                        className="footnote-popover"
                        style={{
                            position: "fixed",
                            top: `${popoverPosition.top}px`,
                            left: `${popoverPosition.left}px`,
                            backgroundColor: "white",
                            border: "1px solid #ccc",
                            borderRadius: "4px",
                            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
                            padding: "8px",
                            zIndex: 1000,
                            minWidth: "300px",
                            maxWidth: "400px",
                        }}
                    >
                    <div style={{ marginBottom: "8px", fontSize: "12px", color: "#666" }}>
                        Edit footnote (Ctrl+Enter to save, Esc to cancel)
                    </div>
                    <textarea
                        ref={inputRef}
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        rows={4}
                        style={{
                            width: "100%",
                            fontSize: "14px",
                            padding: "6px",
                            border: "1px solid #ccc",
                            borderRadius: "3px",
                            resize: "vertical",
                            fontFamily: "inherit",
                        }}
                    />
                    <div
                        style={{
                            display: "flex",
                            gap: "8px",
                            marginTop: "8px",
                            justifyContent: "flex-end",
                        }}
                    >
                        <button
                            onClick={handleCancel}
                            style={{
                                padding: "4px 12px",
                                fontSize: "13px",
                                border: "1px solid #ccc",
                                borderRadius: "3px",
                                backgroundColor: "white",
                                cursor: "pointer",
                            }}
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSave}
                            style={{
                                padding: "4px 12px",
                                fontSize: "13px",
                                border: "1px solid #0066cc",
                                borderRadius: "3px",
                                backgroundColor: "#0066cc",
                                color: "white",
                                cursor: "pointer",
                            }}
                        >
                            Save
                        </button>
                    </div>
                </div>,
                document.body
            )}
        </NodeViewWrapper>
    );
}

const Footnote = Node.create<FootnoteOptions>({
    name: "footnote",
    group: "inline",
    inline: true,
    atom: true, // Cannot be edited directly, must use commands

    addAttributes() {
        return {
            content: {
                default: "",
                parseHTML: (el) => el.textContent || "",
                renderHTML: () => ({}), // Content goes inside the element
            },
        };
    },

    parseHTML() {
        return [
            {
                tag: "span.footnote",
            },
        ];
    },

    renderHTML({ node }) {
        return ["span", { class: "footnote" }, node.attrs.content];
    },

    renderText({ node }) {
        return `[^${node.attrs.content}]`;
    },

    addNodeView() {
        return ReactNodeViewRenderer(FootnoteView);
    },

    addCommands() {
        return {
            insertFootnote:
                (options) =>
                ({ commands }) => {
                    return commands.insertContent({
                        type: this.name,
                        attrs: { content: options.content },
                    });
                },
            updateFootnote:
                (options) =>
                ({ commands }) => {
                    return commands.updateAttributes(this.name, {
                        content: options.content,
                    });
                },
        };
    },
});

export default Footnote;
