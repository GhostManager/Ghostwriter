import { expect, test } from "@playwright/test";
import {
    buildEditorAssets,
    renderEditor,
    type EditorAssets,
} from "./fixtures/editor";

let assets: EditorAssets;
test.beforeAll(async () => {
    assets = await buildEditorAssets();
});

test("deleting the final comment can be saved or cancelled", async ({
    page,
}) => {
    const comments = encodeURIComponent(
        JSON.stringify([
            {
                author: "Unknown",
                comment: "Review this",
                timestamp: "2026-11-06T12:00:00Z",
            },
        ])
    );
    await renderEditor(
        page,
        assets,
        "light",
        `<p><span data-gw-comments="${comments}">Commented text</span> plain text</p>`
    );
    await page.locator(".tiptap .gw-comment").click();
    const dialog = page.getByRole("dialog", { name: "Comments", exact: true });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Delete", exact: true }).click();
    await expect(
        dialog.getByRole("button", { name: "Save", exact: true })
    ).toBeEnabled();
    await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(page.locator(".tiptap .gw-comment")).toHaveText(
        "Commented text"
    );
    await page.locator(".tiptap .gw-comment").click();
    await dialog.getByRole("button", { name: "Delete", exact: true }).click();
    await dialog.getByRole("button", { name: "Save", exact: true }).click();
    await expect(dialog).toBeHidden();
    await expect(page.locator(".tiptap .gw-comment")).toHaveCount(0);
    await expect(page.locator(".tiptap")).toContainText(
        "Commented text plain text"
    );
});

for (const action of ["Save", "Resolve", "Remove All"]) {
    test(`${action} targets the same text after a document insertion`, async ({
        page,
    }) => {
        const comments = encodeURIComponent(
            JSON.stringify([
                {
                    author: "Unknown",
                    comment: "Review this",
                    timestamp: "2026-11-06T12:00:00Z",
                },
            ])
        );
        await renderEditor(
            page,
            assets,
            "light",
            `<p>Before <span data-gw-comments="${comments}">Commented text</span> after</p>`
        );
        await page.locator(".tiptap .gw-comment").click();
        const dialog = page.getByRole("dialog", {
            name: "Comments",
            exact: true,
        });
        await expect(dialog).toBeVisible();
        await page.evaluate(() => {
            const editor = (
                document.querySelector(".tiptap") as HTMLElement & {
                    editor: import("@tiptap/core").Editor;
                }
            ).editor;
            editor.view.dispatch(
                editor.state.tr.insertText("Inserted remotely. ", 1)
            );
        });
        await dialog.getByRole("button", { name: action, exact: true }).click();
        await expect(dialog).toBeHidden();
        await expect(page.locator(".tiptap")).toHaveText(
            "Inserted remotely. Before Commented text after"
        );
        if (action === "Remove All") {
            await expect(page.locator(".tiptap .gw-comment")).toHaveCount(0);
        } else {
            await expect(page.locator(".tiptap .gw-comment")).toHaveText(
                "Commented text"
            );
            if (action === "Resolve")
                await expect(page.locator(".gw-comment-resolved")).toHaveCount(
                    1
                );
        }
    });
}

for (const theme of ["light", "dark"]) {
    for (const width of [1440, 1024, 768, 390]) {
        test(`creates and edits a plain text comment at ${width}px in ${theme}`, async ({
            page,
        }, testInfo) => {
            await page.setViewportSize({ width, height: 900 });
            await renderEditor(page, assets, theme, "<p>Review this text</p>");
            await page.locator(".tiptap").selectText();
            await page
                .getByRole("button", { name: "Comment", exact: true })
                .click();
            const dialog = page.getByRole("dialog", {
                name: "Add Comment",
                exact: true,
            });
            await expect(dialog).toBeVisible();
            const input = dialog.getByLabel("Comment", { exact: true });
            await expect(input).toBeVisible();
            await expect(
                dialog.getByRole("button", { name: "Save", exact: true })
            ).toBeDisabled();
            await input.fill("Test comment");
            await expect(
                dialog.getByRole("button", { name: "Save", exact: true })
            ).toBeEnabled();
            await expect(dialog.locator(".tiptap")).toHaveCount(0);
            const bounds = (await dialog.boundingBox())!;
            expect(bounds.x).toBeGreaterThanOrEqual(0);
            expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
            await expect(
                dialog.getByRole("button", { name: "Save", exact: true })
            ).toBeInViewport();
            await expect(dialog.locator(".modal-content")).toHaveCSS(
                "background-color",
                theme === "dark" ? "rgb(35, 37, 39)" : "rgb(255, 255, 255)"
            );
            await page.screenshot({
                path: testInfo.outputPath(`comment-${theme}-${width}.png`),
            });
            await dialog
                .getByRole("button", { name: "Save", exact: true })
                .click();
            await expect(dialog).toBeHidden();
            await page.locator(".tiptap .gw-comment").click();
            const thread = page.getByRole("dialog", {
                name: "Comments",
                exact: true,
            });
            await expect(thread.locator(".gw-comment-text")).toHaveText(
                "Test comment"
            );
            await thread
                .getByRole("button", { name: "Edit", exact: true })
                .click();
            await thread
                .getByLabel("Edit comment", { exact: true })
                .fill("Updated comment");
            await expect(thread.locator(".tiptap")).toHaveCount(0);
            await thread
                .locator(".gw-comment-edit-buttons")
                .getByRole("button", { name: "Save", exact: true })
                .click();
            await thread
                .getByRole("button", { name: "Save", exact: true })
                .click();
            await page.locator(".tiptap .gw-comment").click();
            await expect(thread.locator(".gw-comment-text")).toHaveText(
                "Updated comment"
            );
        });
    }
}
