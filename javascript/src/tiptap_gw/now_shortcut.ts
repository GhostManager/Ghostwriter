import { Extension, InputRule, type Editor } from "@tiptap/core";
import type { EditorState } from "@tiptap/pm/state";

export const NOW_SHORTCUT_TOKEN = "@now";
export const TIME_SHORTCUT_TOKEN = "@time";
export const NOW_SHORTCUT_TIME_ZONE = "UTC";
export const TODAY_SHORTCUT_TOKEN = "@today";
export const DATE_SHORTCUT_TOKEN = "@date";

type RegExpFactory = (pattern: string, flags?: string) => RegExp;

const createRegExp: RegExpFactory = (pattern, flags) =>
    new RegExp(pattern, flags);

export function createShortcutInputRegex(
    tokens: string,
    regexpFactory: RegExpFactory = createRegExp
): RegExp {
    const unicodeLeadingBoundary = "(?:\\s|\\p{P})";
    const unicodeTriggerBoundary = "(?: |\\p{P})";
    try {
        return regexpFactory(
            `(?:^|${unicodeLeadingBoundary})(@(?:${tokens}))(${unicodeTriggerBoundary})$`,
            "u"
        );
    } catch (error) {
        if (!(error instanceof SyntaxError)) {
            throw error;
        }
        const asciiLeadingBoundary =
            "(?:\\s|[\\x21-\\x2f\\x3a-\\x40\\x5b-\\x60\\x7b-\\x7e])";
        const asciiTriggerBoundary =
            "(?: |[\\x21-\\x2f\\x3a-\\x40\\x5b-\\x60\\x7b-\\x7e])";
        return regexpFactory(
            `(?:^|${asciiLeadingBoundary})(@(?:${tokens}))(${asciiTriggerBoundary})$`
        );
    }
}

export const NOW_SHORTCUT_INPUT_REGEX = createShortcutInputRegex("now|time");
export const TODAY_SHORTCUT_INPUT_REGEX =
    createShortcutInputRegex("today|date");

declare global {
    interface Window {
        GW_EDITOR_SHORTCUTS?: Readonly<{
            activate: () => boolean;
            currentDate: () => string;
            refreshCurrentDate: () => Promise<boolean>;
            resolveCurrentDate: () => Promise<string>;
        }>;
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

function isInCodeContext(state: EditorState): boolean {
    const { $from } = state.selection;
    return (
        Boolean($from.parent.type.spec.code) ||
        $from.marks().some((mark) => Boolean(mark.type.spec.code))
    );
}

export function createNowShortcutInputRule(
    formatTimestamp: () => string = formatNowShortcut
): InputRule {
    return new InputRule({
        find: NOW_SHORTCUT_INPUT_REGEX,
        handler: ({ state, range, match }) => {
            if (isInCodeContext(state)) {
                return null;
            }
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

export function resolveConfiguredCurrentDate(
    currentWindow: Window | undefined = typeof window === "undefined"
        ? undefined
        : window
): Promise<string> {
    const resolveCurrentDate =
        currentWindow?.GW_EDITOR_SHORTCUTS?.resolveCurrentDate;
    return typeof resolveCurrentDate === "function"
        ? resolveCurrentDate()
        : Promise.resolve("");
}

type PendingDateShortcut = Readonly<{
    from: number;
    token: string;
}>;

type PendingDateShortcutHandler = (pending: PendingDateShortcut) => void;

export function replacePendingDateShortcut(
    editor: Editor,
    pending: PendingDateShortcut,
    replacement: string
): boolean {
    const to = pending.from + pending.token.length;
    if (
        !replacement ||
        editor.isDestroyed ||
        editor.state.doc.textBetween(pending.from, to) !== pending.token
    ) {
        return false;
    }

    editor.view.dispatch(
        editor.state.tr.insertText(replacement, pending.from, to)
    );
    return true;
}

export function createTodayShortcutInputRule(
    formatDate: () => string = getConfiguredCurrentDate,
    handlePendingDate?: PendingDateShortcutHandler
): InputRule {
    return new InputRule({
        find: TODAY_SHORTCUT_INPUT_REGEX,
        handler: ({ state, range, match }) => {
            if (isInCodeContext(state)) {
                return null;
            }
            const replacement = formatDate();
            if (!replacement) {
                handlePendingDate?.({
                    from: range.from + match[0].lastIndexOf(match[1]),
                    token: match[1],
                });
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
        if (typeof window !== "undefined") {
            window.GW_EDITOR_SHORTCUTS?.activate();
        }
    },
    addInputRules() {
        const editor = this.editor;
        return [
            createNowShortcutInputRule(),
            createTodayShortcutInputRule(
                getConfiguredCurrentDate,
                (pending) => {
                    void resolveConfiguredCurrentDate().then((replacement) => {
                        replacePendingDateShortcut(
                            editor,
                            pending,
                            replacement
                        );
                    });
                }
            ),
        ];
    },
});

export default DateTimeShortcuts;
