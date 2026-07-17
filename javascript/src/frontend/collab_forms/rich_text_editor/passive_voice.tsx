import { useState } from "react";
import { Editor } from "@tiptap/react";
import { MenuItem } from "@szhsin/react-menu";
import { detectPassiveVoice } from "../../../services/passive_voice_api";
import {
    extractTextWithPositions,
    convertRangesWithMap,
} from "../../../tiptap_gw/text_position_mapper";

interface PassiveVoiceButtonProps {
    editor: Editor;
}

/**
 * Button to scan editor content for passive voice.
 * All detection happens server-side; client applies visual-only decorations.
 * Decorations don't affect the document data and won't be saved/exported.
 * When user edits highlighted text, that specific highlight is removed automatically.
 */
export default function PassiveVoiceButton({
    editor,
}: PassiveVoiceButtonProps) {
    const [isScanning, setIsScanning] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleScan = async () => {
        if (!editor) return;

        setIsScanning(true);
        setError(null);

        // Clear existing passive voice highlights before new scan
        editor.commands.clearPassiveVoice();

        // Extract text and position map together - guarantees they're in sync
        const { text, positionMap } = extractTextWithPositions(
            editor.state.doc
        );

        if (!text.trim()) {
            setIsScanning(false);
            return;
        }

        try {
            // Server does all NLP work, returns character indices relative to plain text
            const ranges = await detectPassiveVoice(text);

            // Convert text offsets to document positions using the pre-built map
            const docRanges = convertRangesWithMap(
                positionMap,
                ranges,
                editor.state.doc.content.size
            );

            // Apply decorations (visual-only, not part of document)
            editor.commands.setPassiveVoiceDocRanges(docRanges);
        } catch (err) {
            console.error("Passive voice detection failed:", err);
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to detect passive voice"
            );
        } finally {
            setIsScanning(false);
        }
    };

    return (
        <>
            <MenuItem
                title="Check for passive voice sentences"
                disabled={!editor || isScanning}
                onClick={handleScan}
            >
                {isScanning ? "Scanning..." : "Check Passive Voice"}
            </MenuItem>
            {error && (
                <MenuItem disabled>
                    <span style={{ color: "#dc3545" }}>Error: {error}</span>
                </MenuItem>
            )}
        </>
    );
}
