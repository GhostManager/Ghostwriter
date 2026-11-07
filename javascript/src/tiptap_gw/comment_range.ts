import type { Mapping } from "@tiptap/pm/transform";

export interface CommentRange {
    from: number;
    to: number;
}

// Exclude insertions at either boundary; include edits inside the selected text.
// A deleted target stays invalid so later edits cannot attach it to other text.
export function mapCommentRange(
    range: CommentRange | null,
    mapping: Mapping
): CommentRange | null {
    if (!range) return null;
    const from = mapping.map(range.from, 1);
    const to = mapping.map(range.to, -1);
    return from < to ? { from, to } : null;
}
