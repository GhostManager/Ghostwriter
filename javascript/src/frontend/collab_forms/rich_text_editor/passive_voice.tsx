import { useState } from "react";
import { Editor } from "@tiptap/react";
import { MenuItem } from "@szhsin/react-menu";
import { detectPassiveVoice } from "../../../services/passive_voice_api";

interface PassiveVoiceButtonProps {
    editor: Editor;
}

/**
 * Button to scan editor content for passive voice.
 * All detection happens server-side; client applies visual-only decorations.
 * Decorations don't affect the document data and won't be saved/exported.
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

        // Clear existing passive voice highlights
        editor.commands.clearPassiveVoice();

        // Get plain text - no client-side processing
        const text = editor.getText();

        if (!text.trim()) {
            setIsScanning(false);
            return;
        }

        try {
            // Server does all NLP work, returns character indices
            const ranges = await detectPassiveVoice(text);

            setLastCount(ranges.length);

            // Apply decorations (visual-only, not part of document)
            editor.commands.setPassiveVoiceRanges(ranges);
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
        editor.commands.clearPassiveVoice();
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
            {lastCount !== null && lastCount > 0 && (
                <MenuItem
                    title="Clear passive voice highlights"
                    disabled={!editor}
                    onClick={handleClear}
                >
                    Clear Highlights ({lastCount})
                </MenuItem>
            )}
            {error && (
                <MenuItem disabled>
                    <span style={{ color: "#dc3545" }}>Error: {error}</span>
                </MenuItem>
            )}
        </>
    );
}
