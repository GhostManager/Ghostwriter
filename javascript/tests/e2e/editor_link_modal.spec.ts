import { expect, test, type Page } from "@playwright/test";
import react from "@vitejs/plugin-react";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";

const javascriptRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../.."
);
const staticRoot = path.join(javascriptRoot, "../ghostwriter/static");
const assets = new Map<string, string | Uint8Array>();

test.beforeAll(async () => {
    // Bundle the real standalone editor without a server, database, or saved edits.
    const result = await build({
        configFile: false,
        root: javascriptRoot,
        plugins: [react()],
        logLevel: "silent",
        build: {
            write: false,
            rollupOptions: {
                input: path.join(
                    javascriptRoot,
                    "src/frontend/standalone_tiptap.tsx"
                ),
                output: { entryFileNames: "editor.js" },
            },
        },
    });
    for (const output of Array.isArray(result) ? result : [result]) {
        if (!("output" in output)) continue;
        for (const asset of output.output) {
            assets.set(
                `/${asset.fileName}`,
                asset.type === "chunk" ? asset.code : asset.source
            );
        }
    }
});

async function renderEditor(page: Page, theme = "light") {
    await page.route("http://ghostwriter.test/**", async (route) => {
        const pathname = new URL(route.request().url()).pathname;
        const asset = assets.get(pathname);
        if (asset !== undefined) {
            await route.fulfill({
                contentType: pathname.endsWith(".css")
                    ? "text/css"
                    : "application/javascript",
                body: typeof asset === "string" ? asset : Buffer.from(asset),
            });
            return;
        }
        await route.fulfill({
            contentType: "text/html",
            body: `<html data-theme="${theme}" data-bs-theme="${theme}"><body><div class="wrapper">
                <nav id="sidebar">Navigation</nav>
                <main id="content">
                    <div class="engagement-context engagement-context-active">
                        <button>Switch report</button><span>Working report</span>
                    </div>
                    <section class="page-content">
                        <h1>Edit narrative</h1>
                        <textarea aria-label="Narrative"><p><a href="https://example.com/original">Existing link</a> plain text</p></textarea>
                    </section>
                </main>
            </div></body></html>`,
        });
    });
    await page.goto("http://ghostwriter.test/");
    for (const stylesheet of [
        "vendor/bootstrap/5.3.8/css/bootstrap.min.css",
        "css/base_styles.css",
        "css/styles.css",
        "css/bootstrap5_compat.css",
        "css/design_system.css",
        "css/app_shell.css",
    ]) {
        await page.addStyleTag({
            content: await readFile(path.join(staticRoot, stylesheet), "utf8"),
        });
    }
    for (const [filename, asset] of assets) {
        if (filename.endsWith(".css")) {
            await page.addStyleTag({ content: String(asset) });
        }
    }
    await page.addScriptTag({
        url: "http://ghostwriter.test/editor.js",
        type: "module",
    });
    await expect(page.locator(".tiptap")).toBeVisible();
}

async function openLinkDialog(page: Page) {
    await page.locator(".tiptap a").click();
    await page.getByRole("button", { name: "Link", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Edit Link", exact: true });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByLabel("URL", { exact: true })).toBeFocused();
    return dialog;
}

test.describe("rich-text link dialog", () => {
    for (const theme of ["light", "dark"]) {
        for (const width of [1440, 1024, 768, 390]) {
            test(`covers the shell and fits the viewport at ${width}px in ${theme} theme`, async ({
                page,
            }, testInfo) => {
                await page.setViewportSize({ width, height: 900 });
                await renderEditor(page, theme);
                const dialog = await openLinkDialog(page);
                await expect(dialog.locator(".modal-content")).toHaveCSS(
                    "background-color",
                    theme === "dark" ? "rgb(35, 37, 39)" : "rgb(255, 255, 255)"
                );
                const bounds = (await dialog.boundingBox())!;
                expect(bounds.width).toBeGreaterThan(Math.min(500, width - 32));
                expect(bounds.x).toBeGreaterThanOrEqual(0);
                expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
                for (const name of ["Remove link", "Cancel", "Save link"]) {
                    await expect(
                        dialog.getByRole("button", { name, exact: true })
                    ).toBeInViewport();
                }
                const layering = await page.evaluate(() => {
                    const overlay = document.querySelector(
                        ".ReactModal__Overlay"
                    )!;
                    const bar = document.querySelector(
                        ".engagement-context-active"
                    )!;
                    const barBounds = bar.getBoundingClientRect();
                    return {
                        barCovered:
                            document.elementFromPoint(
                                barBounds.x + 2,
                                barBounds.y + 2
                            ) === overlay,
                        stripCovered:
                            document.elementFromPoint(
                                barBounds.x + 2,
                                barBounds.y - 2
                            ) === overlay,
                        sidebarCovered:
                            document.elementFromPoint(2, 100) === overlay,
                        backdrop: getComputedStyle(overlay).backgroundColor,
                        overflow:
                            document.documentElement.scrollWidth >
                            window.innerWidth,
                    };
                });
                expect(layering).toEqual({
                    barCovered: true,
                    stripCovered: true,
                    sidebarCovered: true,
                    backdrop: "rgba(21, 23, 24, 0.55)",
                    overflow: false,
                });
                if (width === 1440 || width === 390) {
                    await page.screenshot({
                        path: testInfo.outputPath("edit-link.png"),
                    });
                }
            });
        }
    }

    test("validates unsafe URLs, saves with Enter, and removes links", async ({
        page,
    }) => {
        await renderEditor(page);
        let dialog = await openLinkDialog(page);
        const url = dialog.getByLabel("URL", { exact: true });
        await expect(url).toHaveValue("https://example.com/original");
        await url.fill("javascript:alert(1)");
        await url.press("Enter");
        await expect(dialog.getByRole("alert")).toContainText(
            "Use a relative URL"
        );
        await expect(url).toHaveAttribute("aria-invalid", "true");
        await expect(page.locator(".tiptap a")).toHaveAttribute(
            "href",
            "https://example.com/original"
        );
        await url.fill("https://example.com/updated");
        await url.press("Enter");
        await expect(dialog).toBeHidden();
        await expect(page.locator(".tiptap a")).toHaveAttribute(
            "href",
            "https://example.com/updated"
        );
        dialog = await openLinkDialog(page);
        await dialog
            .getByRole("button", { name: "Remove link", exact: true })
            .click();
        await expect(dialog).toBeHidden();
        await expect(page.locator(".tiptap a")).toHaveCount(0);
        await expect(page.locator(".tiptap")).toContainText("Existing link");
    });

    test("keeps keyboard focus inside the dialog and dismisses without changes", async ({
        page,
    }) => {
        await renderEditor(page);
        for (const dismissal of [
            "Cancel",
            "Close link dialog",
            "Escape",
            "backdrop",
        ]) {
            const dialog = await openLinkDialog(page);
            for (let index = 0; index < 7; index++) {
                await page.keyboard.press("Tab");
                expect(
                    await dialog.evaluate((element) =>
                        element.contains(document.activeElement)
                    )
                ).toBe(true);
            }
            await dialog
                .getByLabel("URL", { exact: true })
                .fill("https://example.com/cancelled");
            if (dismissal === "Escape") {
                await page.keyboard.press("Escape");
            } else if (dismissal === "backdrop") {
                await page
                    .locator(".ReactModal__Overlay")
                    .click({ position: { x: 2, y: 2 } });
            } else {
                await dialog
                    .getByRole("button", { name: dismissal, exact: true })
                    .click();
            }
            await expect(dialog).toBeHidden();
            await expect(page.locator(".tiptap a")).toHaveAttribute(
                "href",
                "https://example.com/original"
            );
        }
    });
});
