import { expect, test, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";

const staticRoot = new URL("../../../ghostwriter/static/", import.meta.url);

async function renderWithTableStyles(page: Page, content: string) {
    await page.setContent(
        `<!doctype html><html><body>${content}</body></html>`
    );
    for (const file of [
        "vendor/bootstrap/5.3.8/css/bootstrap.min.css",
        "css/styles.css",
        "css/design_system.css",
    ]) {
        await page.addStyleTag({
            path: fileURLToPath(new URL(file, staticRoot)),
        });
    }
    await page.addScriptTag({
        path: fileURLToPath(new URL("js/rich-text-tables.js", staticRoot)),
    });
}

async function renderPlanning(page: Page, content: string) {
    await renderWithTableStyles(
        page,
        `
        <main class="p-3">
            <div class="detail-layout project-overview-layout">
                <section class="detail-panel" aria-label="Project Details">Details</section>
                <section class="detail-panel detail-panel-quiet" aria-label="Project Description">
                    <div id="projectDescription" class="detail-prose project-description-content" data-rich-text-tables>
                        ${content}
                    </div>
                </section>
            </div>
        </main>
    `
    );
}

function descriptionTable(columns: number, caption = "Activities") {
    const headers = Array.from(
        { length: columns },
        (_, index) => `<th scope="col">Expected action ${index + 1}</th>`
    ).join("");
    const cells = "<td>Review the activity</td>".repeat(columns);
    return `<table class="table table-bordered"><caption>${caption}</caption>
        <thead><tr>${headers}</tr></thead><tbody><tr>${cells}</tr></tbody></table>`;
}

test("a project description with tables gets a full row and wrapping headers", async ({
    page,
}) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await renderPlanning(page, `<p>Project context</p>${descriptionTable(4)}`);

    const details = (await page
        .getByRole("region", { name: "Project Details" })
        .boundingBox())!;
    const description = (await page
        .getByRole("region", { name: "Project Description", exact: true })
        .boundingBox())!;
    expect(description.y).toBeGreaterThan(details.y + details.height);
    expect(description.x).toBe(details.x);
    expect(description.width).toBe(details.width);
    await expect(page.getByRole("columnheader").first()).toHaveCSS(
        "white-space",
        "normal"
    );
    await expect(page.getByRole("table", { name: "Activities" })).toBeVisible();
});

test("evidence preview contains a wide table nested in metadata", async ({
    page,
}) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const wideTable = descriptionTable(8).replaceAll(
        "Review the activity",
        "A".repeat(70)
    );
    await renderWithTableStyles(
        page,
        `
        <section class="detail-preview-modal evidence-detail-preview-modal m-3">
            <div class="modal-body">
                <div class="detail-preview-modal-content">
                    <table class="table evidence-detail-metadata">
                        <tbody>
                            <tr><td class="evidence-detail-metadata-label">Filename:</td><td>example.txt</td></tr>
                            <tr><td class="evidence-detail-metadata-label">Description:</td>
                                <td data-rich-text-tables>${wideTable}</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>
    `
    );
    const scroller = page.getByRole("region", { name: "Activities" });
    expect(
        await scroller.evaluate(
            (element) => element.scrollWidth - element.clientWidth
        )
    ).toBeGreaterThan(0);
    const metadata = (await page
        .locator(".evidence-detail-metadata")
        .boundingBox())!;
    const modal = (await page.locator(".modal-body").boundingBox())!;
    expect(metadata.x + metadata.width).toBeLessThanOrEqual(
        modal.x + modal.width
    );
    expect(
        await page.evaluate(() => document.documentElement.scrollWidth)
    ).toBeLessThanOrEqual(390);
});

test("wide description tables scroll independently by keyboard on mobile", async ({
    page,
}) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await renderPlanning(
        page,
        `${descriptionTable(8, "First activities")}<p>More context</p>${descriptionTable(8, "Second activities")}`
    );

    const first = page.getByRole("region", {
        name: "First activities",
    });
    const second = page.getByRole("region", {
        name: "Second activities",
    });
    await expect(first.getByRole("table")).toHaveCount(1);
    await expect(second.getByRole("table")).toHaveCount(1);
    await expect(first).toHaveCSS("overflow-x", "auto");
    expect(
        await first.evaluate((element) => element.scrollWidth)
    ).toBeGreaterThan(await first.evaluate((element) => element.clientWidth));
    await page.keyboard.press("Tab");
    await expect(first).toBeFocused();
    await page.keyboard.press("ArrowRight");
    await expect
        .poll(() => first.evaluate((element) => element.scrollLeft))
        .toBeGreaterThan(0);
    expect(await second.evaluate((element) => element.scrollLeft)).toBe(0);
    expect(
        await page.evaluate(() => document.documentElement.scrollWidth)
    ).toBeLessThanOrEqual(390);
});

test("prose-only descriptions keep the desktop side panel", async ({
    page,
}) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await renderPlanning(
        page,
        "<p>Project context with the literal text &lt;table&gt;.</p>"
    );

    const details = (await page
        .getByRole("region", { name: "Project Details" })
        .boundingBox())!;
    const description = (await page
        .getByRole("region", { name: "Project Description", exact: true })
        .boundingBox())!;
    expect(description.y).toBe(details.y);
    expect(description.x).toBeGreaterThan(details.x + details.width);
    await expect(page.locator(".rich-text-table")).toHaveCount(0);
});

test("shared initialization handles inserted previews once and leaves other tables alone", async ({
    page,
}) => {
    await renderPlanning(page, descriptionTable(4));
    await page.evaluate(
        (table) => {
            const preview = document.createElement("div");
            preview.innerHTML = `
            <section data-rich-text-tables>
                ${table}
                <div class="table-responsive">${table}</div>
            </section>
            <section class="inventory">${table}</section>
        `;
            document.body.append(preview);
            const init = (
                window as Window & {
                    gwInitRichTextTables(root?: ParentNode): void;
                }
            ).gwInitRichTextTables;
            init(preview);
            init();
        },
        descriptionTable(4, "Preview activities")
    );

    await expect(page.locator(".rich-text-table")).toHaveCount(2);
    await expect(
        page.locator(".rich-text-table .table-responsive")
    ).toHaveCount(0);
    await expect(page.locator(".inventory > table")).toHaveCount(1);
    await expect(
        page.locator(".table-responsive:not(.rich-text-table) > table")
    ).toHaveCount(1);
});
