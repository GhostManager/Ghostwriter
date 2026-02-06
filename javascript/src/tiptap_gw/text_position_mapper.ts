/**
 * Unified text extraction and position mapping for ProseMirror documents.
 *
 * This module provides a single-pass extraction that returns BOTH the plain text
 * AND the position map, guaranteeing they are always in sync.
 *
 * ProseMirror uses a position model where each node boundary occupies positions
 * in the document. This differs from plain text offsets where only text content
 * is counted.
 *
 * Example:
 *   Document: <p>Hello</p><p>World</p>
 *   Plain text: "Hello\nWorld" (11 characters)
 *
 *   Plain text offset for "World" start = 6 (after "Hello\n")
 *   ProseMirror position for "World" start = 8 (accounting for </p><p> boundaries)
 *
 * By extracting text and building the map in one pass, we eliminate the fragile
 * coupling between getText() and a separate position mapper that must reverse-
 * engineer getText()'s behavior.
 */

import { Node as ProseMirrorNode } from "@tiptap/pm/model";

export interface TextOffsetRange {
    start: number;
    end: number;
}

export interface DocumentPositionRange {
    from: number;
    to: number;
}

export interface TextExtractionResult {
    /** The extracted plain text (equivalent to getText()) */
    text: string;
    /** Map from text offset to document position. map[textOffset] = docPosition */
    positionMap: number[];
}

/**
 * Extract text from a ProseMirror document and build a position map simultaneously.
 *
 * This is the core function that guarantees text and position map are in sync.
 * It walks the document once, collecting text and recording the document position
 * for each character.
 *
 * @param doc - The ProseMirror document
 * @param blockSeparator - The separator to insert between blocks (default: "\n")
 * @returns Object containing both the text and position map
 */
export function extractTextWithPositions(
    doc: ProseMirrorNode,
    blockSeparator: string = "\n"
): TextExtractionResult {
    const textParts: string[] = [];
    const positionMap: number[] = [];
    let isFirstBlock = true;

    doc.descendants((node, pos) => {
        // Check if this is an atom node (like footnotes) that shouldn't be traversed
        const isAtomNode = node.type.spec.atom === true;

        if (isAtomNode && node.isInline) {
            // Inline atom nodes contribute text via renderText() but occupy
            // a single node position in the document.
            //
            // We need to determine what text this node contributes.
            // For known node types, we replicate their renderText() output.
            let textRepr = "";

            if (node.type.name === "footnote") {
                // Footnote renderText: ` [${content}]`
                const content = (node.attrs.content as string) ?? "";
                textRepr = ` [${content}]`;
            } else {
                // For other atom nodes, use textContent or single space placeholder
                textRepr = node.textContent || " ";
            }

            // Add text and map each character to the atom's position
            textParts.push(textRepr);
            for (let i = 0; i < textRepr.length; i++) {
                positionMap.push(pos);
            }

            return false; // Don't descend into atom nodes
        } else if (node.isText && node.text) {
            // Regular text node - map each character to its position
            textParts.push(node.text);
            for (let i = 0; i < node.text.length; i++) {
                positionMap.push(pos + i);
            }
        } else if (node.isBlock) {
            // Block nodes add separators between them (not before the first)
            if (!isFirstBlock) {
                textParts.push(blockSeparator);
                for (let i = 0; i < blockSeparator.length; i++) {
                    positionMap.push(pos);
                }
            }
            isFirstBlock = false;
        }

        return true; // Continue traversing
    });

    // Add one more entry for the end position (for ranges that end after last char)
    positionMap.push(doc.content.size);

    return {
        text: textParts.join(""),
        positionMap,
    };
}

/**
 * Convert text offset ranges to document positions using a pre-built position map.
 *
 * @param positionMap - The position map from extractTextWithPositions()
 * @param textRanges - Array of ranges in plain text offsets
 * @param docSize - The document content size (for clamping)
 * @returns Array of ranges in document positions
 */
export function convertRangesWithMap(
    positionMap: number[],
    textRanges: TextOffsetRange[],
    docSize: number
): DocumentPositionRange[] {
    return textRanges.map(({ start, end }) => {
        // Clamp to valid range
        const safeStart = Math.max(0, Math.min(start, positionMap.length - 1));
        const safeEnd = Math.max(0, Math.min(end, positionMap.length - 1));

        return {
            from: positionMap[safeStart] ?? 0,
            to: positionMap[safeEnd] ?? docSize,
        };
    });
}

// ============================================================================
// Legacy API - kept for backward compatibility but deprecated
// ============================================================================

/**
 * @deprecated Use extractTextWithPositions() instead for guaranteed sync.
 * Build a mapping from plain text offsets to document positions.
 */
export function buildTextToDocPositionMap(
    doc: ProseMirrorNode,
    blockSeparator: string = "\n"
): number[] {
    const { positionMap } = extractTextWithPositions(doc, blockSeparator);
    return positionMap;
}

/**
 * @deprecated Use extractTextWithPositions() + convertRangesWithMap() instead.
 * Convert a plain text offset range to document positions.
 */
export function textOffsetToDocPosition(
    doc: ProseMirrorNode,
    textRange: TextOffsetRange,
    blockSeparator: string = "\n"
): DocumentPositionRange {
    const { positionMap } = extractTextWithPositions(doc, blockSeparator);
    const results = convertRangesWithMap(positionMap, [textRange], doc.content.size);
    return results[0];
}

/**
 * @deprecated Use extractTextWithPositions() + convertRangesWithMap() instead.
 * Convert multiple plain text offset ranges to document positions.
 */
export function textOffsetsToDocPositions(
    doc: ProseMirrorNode,
    textRanges: TextOffsetRange[],
    blockSeparator: string = "\n"
): DocumentPositionRange[] {
    if (textRanges.length === 0) {
        return [];
    }
    const { positionMap } = extractTextWithPositions(doc, blockSeparator);
    return convertRangesWithMap(positionMap, textRanges, doc.content.size);
}
