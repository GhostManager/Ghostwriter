import { Mark } from "@tiptap/core";

export interface CommentEntry {
    author: string;
    comment: string;
    timestamp: string;
}

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        gwComment: {
            setGwComment: (
                comments: CommentEntry[],
                resolved?: boolean
            ) => ReturnType;
            unsetGwComment: () => ReturnType;
        };
    }
}

export function parseComments(raw: string | null | undefined): CommentEntry[] {
    if (!raw) return [];
    try {
        const parsed = JSON.parse(decodeURIComponent(raw));
        if (!Array.isArray(parsed)) return [];
        return parsed.filter(
            (c): c is CommentEntry =>
                typeof c === "object" &&
                c !== null &&
                typeof c.author === "string" &&
                typeof c.comment === "string" &&
                typeof c.timestamp === "string"
        );
    } catch {
        return [];
    }
}

const GwComment = Mark.create({
    name: "gwComment",
    // Allow other marks to coexist with comments
    excludes: "",
    addAttributes() {
        return {
            comments: {
                default: [],
                parseHTML: (element) =>
                    parseComments(element.getAttribute("data-gw-comments")),
                renderHTML: (attributes) => {
                    const comments = attributes.comments as CommentEntry[];
                    if (!Array.isArray(comments) || comments.length === 0)
                        return {};
                    return {
                        "data-gw-comments": encodeURIComponent(
                            JSON.stringify(comments)
                        ),
                    };
                },
            },
            resolved: {
                default: false,
                parseHTML: (element) =>
                    element.hasAttribute("data-gw-comment-resolved"),
                renderHTML: (attributes) =>
                    attributes.resolved
                        ? { "data-gw-comment-resolved": "" }
                        : {},
            },
        };
    },
    parseHTML() {
        return [{ tag: "span[data-gw-comments]" }];
    },
    renderHTML({ HTMLAttributes }) {
        const resolved = "data-gw-comment-resolved" in HTMLAttributes;
        return [
            "span",
            {
                ...HTMLAttributes,
                class: resolved
                    ? "gw-comment gw-comment-resolved"
                    : "gw-comment",
            },
        ];
    },
    addCommands() {
        return {
            setGwComment:
                (comments: CommentEntry[], resolved = false) =>
                ({ commands }) =>
                    commands.setMark(this.name, { comments, resolved }),
            unsetGwComment:
                () =>
                ({ commands }) =>
                    commands.unsetMark(this.name),
        };
    },
});

export default GwComment;
