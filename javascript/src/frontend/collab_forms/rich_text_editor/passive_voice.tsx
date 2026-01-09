import { useState } from "react";
import { Editor } from "@tiptap/react";
import { MenuItem } from "@szhsin/react-menu";
import { detectPassiveVoice } from "../../../services/passive_voice_api";

interface PassiveVoiceButtonProps {
    editor: Editor;
}

/**
 * Button to scan editor content for passive voice.
 * All detection happens server-side; client just applies highlighting.
 */
export default function PassiveVoiceButton({ editor }: PassiveVoiceButtonProps) {
    const [isScanning, setIsScanning] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastCount, setLastCount] = useState<number | null>(null);

    const handleScan = async () => {
        if (!editor) return;

        setIsScanning(true);
        setError(null);
        setLastCount(null);

        // Clear existing passive voice marks
        editor.commands.unsetMark("passiveVoice");

        // Get plain text - no client-side processing
        const text = editor.getText();

        if (!text.trim()) {
            setIsScanning(false);
            return;
        }

        try {
            // Server does all NLP work, returns character indices
            const ranges = await detectPassiveVoice(text);

            if (ranges.length === 0) {
                setLastCount(0);
            } else {
                setLastCount(ranges.length);

                // Apply all marks in a single transaction
                const { state } = editor;
                const { tr, schema } = state;
                const markType = schema.marks.passiveVoice;

                if (markType) {
                    // TipTap uses 1-based indexing, server uses 0-based
                    ranges.forEach(({ start, end }) => {
                        const from = start + 1;
                        const to = end + 1;

                        // Apply mark directly to transaction
                        tr.addMark(from, to, markType.create());
                    });

                    // Dispatch the transaction with all marks applied
                    editor.view.dispatch(tr);

                    // Clear storedMarks in a separate transaction to ensure it takes effect
                    const { state: newState } = editor;
                    const clearTr = newState.tr;
                    clearTr.removeStoredMark(markType);
                    editor.view.dispatch(clearTr);
                }
            }
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

    const handleClear = () => {
        if (!editor) return;
        editor.commands.unsetMark("passiveVoice");
        setLastCount(null);
        setError(null);
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
