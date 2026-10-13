import { expect, type Page } from "@playwright/test";
import react from "@vitejs/plugin-react";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";

const javascriptRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../../.."
);
const staticRoot = path.join(javascriptRoot, "../ghostwriter/static");
export type EditorAssets = Map<string, string | Uint8Array>;

export async function buildEditorAssets(): Promise<EditorAssets> {
    const assets: EditorAssets = new Map();
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
    return assets;
}

export async function renderEditor(
    page: Page,
    assets: EditorAssets,
    theme = "light",
    content = '<p><a href="https://example.com/original">Existing link</a> plain text</p>'
) {
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
                        <textarea aria-label="Narrative">${content}</textarea>
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
