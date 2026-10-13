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

const content = `<h2 data-bookmark="original-heading">Test heading</h2>
    <div class="collab-table-wrapper"><table><tbody><tr><td><p>Cell text</p></td></tr></tbody></table>
    <p class="collab-table-caption" data-bookmark="original-caption"><span class="collab-table-caption-prefix">Table #:</span><span class="collab-table-caption-content">Test caption</span></p></div>`;
const targets = [
    {
        name: "heading",
        selector: ".tiptap h2",
        menu: "Heading",
        title: "Edit Heading Bookmark",
        original: "original-heading",
    },
    {
        name: "table caption",
        selector: ".tiptap .collab-table-caption",
        menu: "Table",
        title: "Edit Table Caption Bookmark",
        original: "original-caption",
    },
];

async function openBookmarkDialog(
    page: Page,
    target: (typeof targets)[number]
) {
    await page.locator(target.selector).click();
    await page.getByRole("button", { name: target.menu, exact: true }).click();
    await page
        .getByRole("menuitem", { name: "Set Bookmark", exact: true })
        .click();
    const dialog = page.getByRole("dialog", {
        name: target.title,
        exact: true,
    });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByLabel("Bookmark name")).toBeFocused();
    return dialog;
}

for (const target of targets) {
    test.describe(`${target.name} bookmark dialog`, () => {
        for (const theme of ["light", "dark"]) {
            for (const width of [1440, 390]) {
                test(`fits ${width}px in ${theme} theme`, async ({
                    page,
                }, testInfo) => {
                    await page.setViewportSize({ width, height: 900 });
                    await renderEditor(page, assets, theme, content);
                    const dialog = await openBookmarkDialog(page, target);
                    await expect(dialog.locator(".modal-content")).toHaveCSS(
                        "background-color",
                        theme === "dark"
                            ? "rgb(35, 37, 39)"
                            : "rgb(255, 255, 255)"
                    );
                    const bounds = (await dialog.boundingBox())!;
                    expect(bounds.width).toBeGreaterThan(
                        Math.min(500, width - 32)
                    );
                    expect(bounds.x).toBeGreaterThanOrEqual(0);
                    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
                    await expect(
                        dialog.getByRole("button", {
                            name: "Cancel",
                            exact: true,
                        })
                    ).toBeInViewport();
                    await expect(
                        dialog.getByRole("button", {
                            name: "Save bookmark",
                            exact: true,
                        })
                    ).toBeInViewport();
                    expect(
                        await page.evaluate(
                            () =>
                                document.documentElement.scrollWidth >
                                window.innerWidth
                        )
                    ).toBe(false);
                    await page.screenshot({
                        path: testInfo.outputPath("bookmark-dialog.png"),
                    });
                });
            }
        }

        test("prefills, trims and saves with Enter, and clears bookmarks", async ({
            page,
        }) => {
            await renderEditor(page, assets, "light", content);
            let dialog = await openBookmarkDialog(page, target);
            const input = dialog.getByLabel("Bookmark name");
            await expect(input).toHaveValue(target.original);
            await input.fill("  updated-bookmark  ");
            await input.press("Enter");
            await expect(dialog).toBeHidden();
            await expect(page.locator(target.selector)).toHaveAttribute(
                "data-bookmark",
                "updated-bookmark"
            );
            dialog = await openBookmarkDialog(page, target);
            await expect(dialog.getByLabel("Bookmark name")).toHaveValue(
                "updated-bookmark"
            );
            await dialog.getByLabel("Bookmark name").fill("   ");
            await dialog
                .getByRole("button", { name: "Save bookmark", exact: true })
                .click();
            await expect(dialog).toBeHidden();
            await expect(page.locator(target.selector)).not.toHaveAttribute(
                "data-bookmark"
            );
        });

        test("traps focus and dismisses without changing bookmarks", async ({
            page,
        }) => {
            await renderEditor(page, assets, "light", content);
            for (const dismissal of [
                "Cancel",
                "Close bookmark dialog",
                "Escape",
                "backdrop",
            ]) {
                const dialog = await openBookmarkDialog(page, target);
                for (let index = 0; index < 6; index++) {
                    await page.keyboard.press("Tab");
                    expect(
                        await dialog.evaluate((element) =>
                            element.contains(document.activeElement)
                        )
                    ).toBe(true);
                }
                await dialog
                    .getByLabel("Bookmark name")
                    .fill("cancelled-bookmark");
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
                await expect(page.locator(target.selector)).toHaveAttribute(
                    "data-bookmark",
                    target.original
                );
            }
        });
    });
}

test("table bookmark becomes available after adding and selecting a caption", async ({
    page,
}) => {
    await renderEditor(page, assets, "light", "<p>Table example</p>");
    await page.locator(".tiptap p").click();
    const tableMenu = page.getByRole("button", { name: "Table", exact: true });
    await tableMenu.click();
    await expect(
        page.getByRole("menuitem", { name: "Set Bookmark", exact: true })
    ).toHaveAttribute("aria-disabled", "true");
    await page.getByRole("menuitem", { name: "Insert", exact: true }).click();
    await page.locator(".tiptap th").first().click();
    await tableMenu.click();
    await expect(
        page.getByRole("menuitem", { name: "Set Bookmark", exact: true })
    ).toHaveAttribute("aria-disabled", "true");
    await page
        .getByRole("menuitem", { name: "Add Caption", exact: true })
        .click();
    await expect(page.locator(".tiptap .collab-table-caption")).toBeVisible();
    await openBookmarkDialog(page, targets[1]);
});
