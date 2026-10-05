import { expect, test, type Page } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { compile } from "sass";

const javascriptRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../.."
);
const editorCss = compile(
    path.join(javascriptRoot, "src/frontend/collab_forms/editor.scss"),
    { loadPaths: [path.join(javascriptRoot, "node_modules")] }
).css;

async function renderWritingPane(page: Page, theme = "light") {
    // Match the report field's React containers and use the production styles.
    await page.setContent(`
        <html data-theme="${theme}"><body>
            <div class="report-field-workspace" style="--gw-report-workspace-top: 20px; --gw-report-workspace-bottom: 20px">
                <header><h1>Edit narrative</h1></header>
                <div class="resource-form-shell">
                    <div id="collab-form-container">
                        <div class="form-group col-md-12 report-field-form-group">
                            <div class="collab-editor">
                                <div class="control-group"><button>Bold</button></div>
                                <div class="collab-editor-content">
                                    <div class="tiptap ProseMirror" contenteditable="true"><p>Short narrative.</p></div>
                                </div>
                            </div>
                        </div>
                        <footer class="report-field-footer">Connected</footer>
                    </div>
                </div>
            </div>
        </body></html>
    `);
    await page.addStyleTag({
        path: path.join(
            javascriptRoot,
            "../ghostwriter/static/vendor/bootstrap/5.3.8/css/bootstrap.min.css"
        ),
    });
    await page.addStyleTag({ content: editorCss });
    await page.addStyleTag({ content: "body { margin: 20px; }" });
}

test.describe("report field writing pane", () => {
    for (const theme of ["light", "dark"]) {
        test(`blank space accepts focus and typing in ${theme} theme`, async ({
            page,
        }) => {
            await page.setViewportSize({ width: 1440, height: 900 });
            await renderWritingPane(page, theme);
            const content = page.locator(".collab-editor-content");
            const bounds = (await content.boundingBox())!;
            expect(bounds.height).toBeGreaterThan(400);

            await content.click({
                position: { x: 40, y: bounds.height - 30 },
            });
            const editor = page.locator(".tiptap");
            await expect(editor).toBeFocused();
            await page.keyboard.type(" More narrative.");
            await expect(editor).toContainText("More narrative.");
        });
    }

    test("long narratives scroll inside the pane while controls stay visible", async ({
        page,
    }) => {
        await page.setViewportSize({ width: 1440, height: 900 });
        await renderWritingPane(page);
        await page.locator(".tiptap").evaluate((editor) => {
            for (let index = 0; index < 60; index++) {
                const paragraph = document.createElement("p");
                paragraph.textContent = `Narrative paragraph ${index}`;
                editor.appendChild(paragraph);
            }
        });
        const toolbar = page.locator(".control-group");
        const before = (await toolbar.boundingBox())!;
        await page.locator(".collab-editor-content").evaluate((content) => {
            content.scrollTop = content.scrollHeight;
        });

        expect(
            await page
                .locator(".collab-editor-content")
                .evaluate((content) => content.scrollTop)
        ).toBeGreaterThan(0);
        expect((await toolbar.boundingBox())!.y).toBe(before.y);
        await expect(toolbar).toBeInViewport();
        expect(
            await page.evaluate(() => document.documentElement.scrollHeight)
        ).toBeLessThanOrEqual(900);
    });

    test("narrow windows retain page scrolling without horizontal overflow", async ({
        page,
    }) => {
        await page.setViewportSize({ width: 390, height: 844 });
        await renderWritingPane(page);
        await page.locator(".tiptap").click();
        await expect(page.locator(".tiptap")).toBeFocused();
        expect(
            await page.evaluate(() => document.documentElement.scrollWidth)
        ).toBeLessThanOrEqual(390);
    });
});
