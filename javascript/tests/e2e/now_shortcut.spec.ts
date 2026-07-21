import { expect, test } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
    createNowShortcutInputRule,
    createTodayShortcutInputRule,
    formatNowShortcut,
    getConfiguredCurrentDate,
    NOW_SHORTCUT_INPUT_REGEX,
    TODAY_SHORTCUT_INPUT_REGEX,
} from "../../src/tiptap_gw/now_shortcut";

const browserShortcutScript = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../../../ghostwriter/static/js/editor_shortcuts.js"
);

function runInputRule(
    rule: ReturnType<typeof createNowShortcutInputRule>,
    to: number,
    token: string,
    delimiter: string,
    delimiterAlreadyInserted = false
) {
    let insertion: { text: string; from: number; to: number } | undefined;
    const matchText = ` ${token}${delimiter}`;
    const rangeTo = delimiterAlreadyInserted ? to + delimiter.length : to;
    rule.handler({
        state: {
            tr: {
                insertText: (text: string, from: number, insertTo: number) => {
                    insertion = { text, from, to: insertTo };
                },
            },
        } as never,
        range: {
            from:
                rangeTo -
                (matchText.length -
                    (delimiterAlreadyInserted ? 0 : delimiter.length)),
            to: rangeTo,
        },
        match: [matchText, token, delimiter] as never,
        commands: {} as never,
        chain: (() => undefined) as never,
        can: (() => undefined) as never,
    });
    return insertion;
}

test.describe("date and time rich-text shortcuts", () => {
    test("formats a zero-padded UTC time", () => {
        expect(formatNowShortcut(new Date("2026-07-21T20:14:13.000Z"))).toBe(
            "20:14:13 UTC"
        );
        expect(formatNowShortcut(new Date("2026-07-21T00:01:02.000Z"))).toBe(
            "00:01:02 UTC"
        );
    });

    test("matches complete lowercase tokens followed by spaces or punctuation", () => {
        expect(NOW_SHORTCUT_INPUT_REGEX.test("@now ")).toBe(true);
        expect(NOW_SHORTCUT_INPUT_REGEX.test("@time ")).toBe(true);
        expect(NOW_SHORTCUT_INPUT_REGEX.test("On July 21, at @now.")).toBe(
            true
        );
        expect(TODAY_SHORTCUT_INPUT_REGEX.test("On @today, at")).toBe(false);
        expect(TODAY_SHORTCUT_INPUT_REGEX.test("On @today,")).toBe(true);
        expect(TODAY_SHORTCUT_INPUT_REGEX.test("On @date,")).toBe(true);
        expect(TODAY_SHORTCUT_INPUT_REGEX.test("(@today)")).toBe(true);
        expect(NOW_SHORTCUT_INPUT_REGEX.test("email@now ")).toBe(false);
        expect(TODAY_SHORTCUT_INPUT_REGEX.test("email@today.")).toBe(false);
        expect(NOW_SHORTCUT_INPUT_REGEX.test("@now")).toBe(false);
        expect(NOW_SHORTCUT_INPUT_REGEX.test("@Now ")).toBe(false);
    });

    test("replaces @now and preserves the triggering punctuation", () => {
        const rule = createNowShortcutInputRule(() => "20:14:13 UTC");
        expect(runInputRule(rule, 18, "@now", ".")).toEqual({
            text: "20:14:13 UTC.",
            from: 14,
            to: 18,
        });
    });

    test("replaces shortcuts after composed punctuation input", () => {
        const rule = createNowShortcutInputRule(() => "20:14:13 UTC");
        expect(runInputRule(rule, 18, "@now", ".", true)).toEqual({
            text: "20:14:13 UTC.",
            from: 14,
            to: 19,
        });
    });

    test("replaces @time as an alias of @now", () => {
        const rule = createNowShortcutInputRule(() => "20:14:13 UTC");
        expect(runInputRule(rule, 19, "@time", " ")).toEqual({
            text: "20:14:13 UTC ",
            from: 14,
            to: 19,
        });
    });

    test("replaces @today with the server-formatted date", () => {
        const rule = createTodayShortcutInputRule(() => "21 Jul 2026");
        expect(runInputRule(rule, 20, "@today", ",")).toEqual({
            text: "21 Jul 2026,",
            from: 14,
            to: 20,
        });
    });

    test("replaces @date as an alias of @today", () => {
        const rule = createTodayShortcutInputRule(() => "21 Jul 2026");
        expect(runInputRule(rule, 19, "@date", ".")).toEqual({
            text: "21 Jul 2026.",
            from: 14,
            to: 19,
        });
    });

    test("reads the Django-formatted date from the page configuration", () => {
        const currentWindow = {
            GW_EDITOR_SHORTCUTS: {
                activate: () => true,
                currentDate: () => "2026/07/21",
                refreshCurrentDate: () => Promise.resolve(true),
            },
        } as unknown as Window;

        expect(getConfiguredCurrentDate(currentWindow)).toBe("2026/07/21");
        expect(getConfiguredCurrentDate(undefined)).toBe("");
    });

    test("does not refresh until an editor activates the shortcuts", async ({
        page,
    }) => {
        const now = Date.now();
        let refreshRequests = 0;
        const initialConfig = {
            date: "21 Jul 2026",
            expiresAt: now - 1000,
            serverTime: now,
            refreshUrl: "http://ghostwriter.test/refresh-date",
        };
        const refreshedConfig = {
            date: "22 Jul 2026",
            expiresAt: now + 24 * 60 * 60 * 1000,
            serverTime: now,
            refreshUrl: initialConfig.refreshUrl,
        };

        await page.route("http://ghostwriter.test/**", async (route) => {
            const url = new URL(route.request().url());
            if (url.pathname === "/refresh-date") {
                refreshRequests += 1;
                await route.fulfill({ json: refreshedConfig });
                return;
            }
            await route.fulfill({
                contentType: "text/html",
                body: `<script id="gw-current-date" type="application/json">${JSON.stringify(initialConfig)}</script>`,
            });
        });

        await page.goto("http://ghostwriter.test/");
        await page.addScriptTag({ path: browserShortcutScript });

        await page.waitForTimeout(300);
        expect(refreshRequests).toBe(0);

        await page.evaluate(() => window.GW_EDITOR_SHORTCUTS?.activate());

        await expect
            .poll(() =>
                page.evaluate(() => window.GW_EDITOR_SHORTCUTS?.currentDate())
            )
            .toBe("22 Jul 2026");
        expect(refreshRequests).toBe(1);
    });
});
