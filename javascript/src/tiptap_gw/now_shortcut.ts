import { Extension, InputRule } from "@tiptap/core";

export const NOW_SHORTCUT_TOKEN = "@now";
export const TIME_SHORTCUT_TOKEN = "@time";
export const NOW_SHORTCUT_TIME_ZONE = "UTC";
export const TODAY_SHORTCUT_TOKEN = "@today";
export const DATE_SHORTCUT_TOKEN = "@date";
export const NOW_SHORTCUT_INPUT_REGEX =
    /(?:^|[\s\p{P}])(@(?:now|time))([\s\p{P}])$/u;
export const TODAY_SHORTCUT_INPUT_REGEX =
    /(?:^|[\s\p{P}])(@(?:today|date))([\s\p{P}])$/u;

declare global {
    interface Window {
        GW_EDITOR_SHORTCUTS?: {
            activate: () => boolean;
            currentDate: () => string;
        };
    }
}

/** Format a date for insertion by the @now rich-text shortcut. */
export function formatNowShortcut(date: Date = new Date()): string {
    const parts: Record<string, string> = {};
    const formatter = new Intl.DateTimeFormat("en-US", {
        timeZone: NOW_SHORTCUT_TIME_ZONE,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hourCycle: "h23",
    });

    formatter.formatToParts(date).forEach((part) => {
        if (part.type !== "literal") {
            parts[part.type] = part.value;
        }
    });

    return `${parts.hour}:${parts.minute}:${parts.second} ${NOW_SHORTCUT_TIME_ZONE}`;
}

export function createNowShortcutInputRule(
    formatTimestamp: () => string = formatNowShortcut
): InputRule {
    return new InputRule({
        find: NOW_SHORTCUT_INPUT_REGEX,
        handler: ({ state, range, match }) => {
            const replacement = formatTimestamp();
            if (!replacement) {
                return null;
            }

            const tokenStart = range.from + match[0].lastIndexOf(match[1]);
            state.tr.insertText(
                `${replacement}${match[2]}`,
                tokenStart,
                range.to
            );
        },
    });
}

/** Return today's date as formatted by Django using the configured DATE_FORMAT. */
export function getConfiguredCurrentDate(
    currentWindow: Window | undefined = typeof window === "undefined"
        ? undefined
        : window
): string {
    return currentWindow?.GW_EDITOR_SHORTCUTS?.currentDate() ?? "";
}

export function createTodayShortcutInputRule(
    formatDate: () => string = getConfiguredCurrentDate
): InputRule {
    return new InputRule({
        find: TODAY_SHORTCUT_INPUT_REGEX,
        handler: ({ state, range, match }) => {
            const replacement = formatDate();
            if (!replacement) {
                return null;
            }

            const tokenStart = range.from + match[0].lastIndexOf(match[1]);
            state.tr.insertText(
                `${replacement}${match[2]}`,
                tokenStart,
                range.to
            );
        },
    });
}

const DateTimeShortcuts = Extension.create({
    name: "dateTimeShortcuts",
    onCreate() {
        window.GW_EDITOR_SHORTCUTS?.activate();
    },
    addInputRules() {
        return [createNowShortcutInputRule(), createTodayShortcutInputRule()];
    },
});

export default DateTimeShortcuts;
