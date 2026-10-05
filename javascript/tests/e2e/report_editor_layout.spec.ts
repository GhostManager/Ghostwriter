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
const staticRoot = path.join(javascriptRoot, "../ghostwriter/static");

async function renderWritingPane(page: Page, theme = "light") {
    // Match the report field's React containers and use the production styles.
    await page.setContent(`
        <html data-theme="${theme}" data-bs-theme="${theme}"><body>
          <div class="wrapper"><main id="content">
            <aside class="engagement-context engagement-context-active">
                <div class="engagement-context-label">Working on</div>
                <div class="engagement-context-empty">Working report</div>
            </aside>
            <section class="page-content report-field-workspace">
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
            </section>
          </main></div>
        </body></html>
    `);
    for (const stylesheet of [
        "vendor/bootstrap/5.3.8/css/bootstrap.min.css",
        "css/base_styles.css",
        "css/styles.css",
        "css/bootstrap5_compat.css",
        "css/design_system.css",
        "css/app_shell.css",
    ]) {
        await page.addStyleTag({ path: path.join(staticRoot, stylesheet) });
    }
    await page.addStyleTag({ content: editorCss });
    await page.addScriptTag({
        path: path.join(staticRoot, "js/page-sticky-offset.js"),
    });
    // Loading the shell styles starts transitions; measure only settled geometry.
    await page.evaluate(async () => {
        await document.fonts.ready;
    });
    await expect
        .poll(() => page.evaluate(() => document.getAnimations().length))
        .toBe(0);
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

    test("real observers resize the workspace when the engagement bar wraps", async ({
        page,
    }) => {
        await page.setViewportSize({ width: 1440, height: 900 });
        await renderWritingPane(page);
        const bar = page.locator(".engagement-context");
        const workspace = page.locator(".report-field-workspace");
        const beforeBar = (await bar.boundingBox())!;
        const beforeWorkspace = (await workspace.boundingBox())!;

        // Change content without a resize event: ResizeObserver must do the work.
        await page.locator(".engagement-context-empty").evaluate((label) => {
            label.textContent =
                "Working report with a long client and project name. ".repeat(
                    16
                );
        });
        await expect
            .poll(async () => (await bar.boundingBox())!.height)
            .toBeGreaterThan(beforeBar.height);
        await expect
            .poll(async () => (await workspace.boundingBox())!.height)
            .toBeLessThan(beforeWorkspace.height);

        for (const width of [1440, 1024]) {
            await page.setViewportSize({ width, height: 900 });
            await expect
                .poll(() =>
                    page.evaluate(() => {
                        const bar = document.querySelector<HTMLElement>(
                            ".engagement-context"
                        )!;
                        const content = document.getElementById("content")!;
                        const offset = parseFloat(
                            content.style.getPropertyValue(
                                "--gw-page-sticky-top"
                            )
                        );
                        const gap = parseFloat(getComputedStyle(bar).top);
                        return Math.abs(
                            offset -
                                bar.getBoundingClientRect().height -
                                gap * 2
                        );
                    })
                )
                .toBeLessThan(1);
            await expect
                .poll(() =>
                    page.evaluate(() => {
                        const content = document.getElementById("content")!;
                        const workspace = document.querySelector(
                            ".report-field-workspace"
                        )!;
                        const bottom =
                            window.innerHeight -
                            parseFloat(getComputedStyle(content).paddingBottom);
                        return Math.abs(
                            workspace.getBoundingClientRect().bottom - bottom
                        );
                    })
                )
                .toBeLessThan(1);
        }
    });

    test("real class observer keeps the scrolling toolbar below active context", async ({
        page,
    }) => {
        // Short windows use page scrolling and a sticky toolbar.
        await page.setViewportSize({ width: 1024, height: 600 });
        await renderWritingPane(page);
        await page.locator(".tiptap").evaluate((editor) => {
            for (let index = 0; index < 60; index++) {
                const paragraph = document.createElement("p");
                paragraph.textContent = `Narrative paragraph ${index}`;
                editor.appendChild(paragraph);
            }
        });
        await page.evaluate(() =>
            window.scrollTo({ top: 500, behavior: "instant" })
        );
        await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(500);
        const bar = page.locator(".engagement-context");
        const toolbar = page.locator(".control-group");
        const activeTop = await bar.evaluate(
            (bar) =>
                bar.getBoundingClientRect().height +
                2 * parseFloat(getComputedStyle(bar).top)
        );
        await expect
            .poll(async () => (await toolbar.boundingBox())!.y)
            .toBeCloseTo(activeTop, 0);

        // Position changes without a size change, requiring MutationObserver.
        await bar.evaluate((bar) =>
            bar.classList.remove("engagement-context-active")
        );
        await expect(page.locator("#content")).toHaveCSS(
            "--gw-page-sticky-top",
            "0px"
        );
        await expect
            .poll(async () => (await toolbar.boundingBox())!.y)
            .toBeCloseTo(0, 0);
        await bar.evaluate((bar) =>
            bar.classList.add("engagement-context-active")
        );
        await expect
            .poll(async () => (await toolbar.boundingBox())!.y)
            .toBeCloseTo(activeTop, 0);
        await expect(toolbar).toBeInViewport();
    });
});
