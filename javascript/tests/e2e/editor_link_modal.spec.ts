import { expect, test, type Page } from "@playwright/test";
import {
    buildEditorAssets,
    renderEditor,
    type EditorAssets,
} from "./fixtures/editor";

let assets: EditorAssets;
test.beforeAll(async () => {
    assets = await buildEditorAssets();
});

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
                await renderEditor(page, assets, theme);
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
        await renderEditor(page, assets);
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
        await renderEditor(page, assets);
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
