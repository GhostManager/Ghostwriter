/**
 * API service for passive voice detection.
 * Server does all NLP processing, returns character ranges only.
 */

export interface PassiveVoiceRange {
    start: number;
    end: number;
}

export interface PassiveVoiceResponse {
    ranges: [number, number][];
    count: number;
}

/**
 * Detect passive voice sentences in text.
 * @param text - Plain text to analyze (server-side processing)
 * @returns Array of character ranges for passive sentences
 */
export async function detectPassiveVoice(
    text: string
): Promise<PassiveVoiceRange[]> {
    const response = await fetch("/api/v1/passive-voice/detect", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ text }),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
            errorData.error || `Detection failed: ${response.statusText}`
        );
    }

    const data: PassiveVoiceResponse = await response.json();

    // Convert server ranges to client format
    return data.ranges.map(([start, end]) => ({ start, end }));
}

function getCsrfToken(): string {
    const cookie = document.cookie
        .split("; ")
        .find((row) => row.startsWith("csrftoken="));
    return cookie ? cookie.split("=")[1] : "";
}
