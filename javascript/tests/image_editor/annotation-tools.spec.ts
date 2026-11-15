import { expect, test, Page } from "@playwright/test";
import {
    constrainRegion,
    markerRadius,
    nextMarkerNumber,
} from "../../src/frontend/image_annotator/render";
import type { AnnotationOp } from "../../src/frontend/image_annotator/render";

const marker = (number: number): AnnotationOp => ({
    kind: "marker",
    x: 100,
    y: 50,
    radius: 12,
    color: "#0044ff",
    number,
});

async function open(page: Page, query = "") {
    await page.goto("/" + query);
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
}
async function position(page: Page, x: number, y: number) {
    const box = (await page.locator("canvas").boundingBox())!;
    return {
        x: box.x + (x * box.width) / 400,
        y: box.y + (y * box.height) / 300,
    };
}
async function pixel(page: Page, x: number, y: number) {
    return page
        .locator("canvas")
        .evaluate(
            (canvas: HTMLCanvasElement, [x, y]) => [
                ...canvas.getContext("2d")!.getImageData(x, y, 1, 1).data,
            ],
            [x, y]
        );
}
async function drag(page: Page, values: number[], shift = false) {
    const start = await position(page, values[0], values[1]);
    const end = await position(page, values[2], values[3]);
    await page.mouse.move(start.x, start.y);
    if (shift) await page.keyboard.down("Shift");
    await page.mouse.down();
    await page.mouse.move(end.x, end.y);
    await page.mouse.up();
    if (shift) await page.keyboard.up("Shift");
}

test("snapping uses common directions and preserves constraints at image edges", () => {
    for (const [dx, dy] of [
        [80, 5],
        [80, 55],
        [5, 80],
        [-55, 80],
        [-80, 5],
        [-80, -55],
        [-5, -80],
        [55, -80],
    ]) {
        for (const kind of ["line", "arrow"] as const) {
            const result = constrainRegion(
                { x0: 50, y0: 50, x1: 50 + dx, y1: 50 + dy },
                kind,
                { width: 100, height: 100 }
            );
            const x = Math.abs(result.x1 - result.x0),
                y = Math.abs(result.y1 - result.y0);
            expect(x === 0 || y === 0 || Math.abs(x - y) < 1e-9).toBe(true);
            expect(result.x1).toBeGreaterThanOrEqual(0);
            expect(result.y1).toBeGreaterThanOrEqual(0);
            expect(result.x1).toBeLessThanOrEqual(100);
            expect(result.y1).toBeLessThanOrEqual(100);
        }
    }
    const square = constrainRegion({ x0: 90, y0: 20, x1: 98, y1: 80 }, "rect", {
        width: 100,
        height: 100,
    });
    expect(square).toEqual({ x0: 90, y0: 20, x1: 100, y1: 30 });
});

test("number sequence follows committed history and tiny markers fit the image", () => {
    expect(nextMarkerNumber([])).toBe(1);
    expect(nextMarkerNumber([marker(1)])).toBe(2);
    expect(nextMarkerNumber([marker(1), marker(2)])).toBe(3);
    expect(nextMarkerNumber([marker(4), marker(2)])).toBe(5);
    expect(markerRadius(2, 2)).toBe(1);
    expect(markerRadius(800, 500)).toBeGreaterThanOrEqual(12);
});

test("lines export the exact custom color without an arrowhead", async ({
    page,
}) => {
    await open(page);
    const result = await page.evaluate(() =>
        window.imageEditorTest.exported(
            [
                {
                    kind: "line",
                    x0: 20,
                    y0: 40,
                    x1: 180,
                    y1: 40,
                    width: 4,
                    color: "#00cc88",
                },
            ],
            [
                [100, 40],
                [100, 46],
                [170, 46],
            ]
        )
    );
    expect(result.pixels).toEqual([
        [0, 204, 136, 255],
        [255, 255, 255, 255],
        [255, 255, 255, 255],
    ]);
});

test("numbered circles export visible contrasting labels, including multiple digits", async ({
    page,
}) => {
    await open(page);
    const [one, two, many] = await page.evaluate(() =>
        Promise.all(
            [1, 2, 123].map((number) =>
                window.imageEditorTest.exported(
                    [
                        {
                            kind: "marker",
                            x: 100,
                            y: 50,
                            number,
                            color: "#0044ff",
                            radius: 12,
                        },
                    ],
                    [
                        [109, 54],
                        [120, 50],
                    ]
                )
            )
        )
    );
    expect(one.png).not.toBe(two.png);
    expect(two.png).not.toBe(many.png);
    expect(one.pixels).toEqual([
        [0, 68, 255, 255],
        [255, 255, 255, 255],
    ]);
});

test("custom color picker and hex input stay synchronized and reject invalid colors", async ({
    page,
}) => {
    await open(page);
    await page.getByRole("button", { name: "Line", exact: true }).click();
    await page
        .getByLabel("Custom annotation color", { exact: true })
        .fill("#12ab34");
    await expect(
        page.getByLabel("Annotation color hex", { exact: true })
    ).toHaveValue("#12ab34");
    await page
        .getByLabel("Annotation color hex", { exact: true })
        .fill("#ab12ef");
    await page
        .getByLabel("Annotation color hex", { exact: true })
        .press("Enter");
    await expect(
        page.getByLabel("Custom annotation color", { exact: true })
    ).toHaveValue("#ab12ef");
    await page
        .getByLabel("Annotation color hex", { exact: true })
        .fill("invalid");
    await page
        .getByLabel("Annotation color hex", { exact: true })
        .press("Enter");
    await expect(page.getByRole("alert")).toContainText("hex color");
    await expect(
        page.getByLabel("Custom annotation color", { exact: true })
    ).toHaveValue("#ab12ef");
});

test("Shift toggles line constraints while dragging and commits the constrained endpoint", async ({
    page,
}) => {
    await open(page);
    await page.getByRole("button", { name: "Line", exact: true }).click();
    await page
        .getByLabel("Custom annotation color", { exact: true })
        .fill("#0088cc");
    const start = await position(page, 100, 100),
        end = await position(page, 240, 125);
    await page.mouse.move(start.x, start.y);
    await page.mouse.down();
    await page.mouse.move(end.x, end.y);
    await page.keyboard.down("Shift");
    expect(await pixel(page, 200, 100)).toEqual([0, 136, 204, 255]);
    expect(await pixel(page, 200, 118)).toEqual([255, 255, 255, 255]);
    await page.keyboard.up("Shift");
    expect(await pixel(page, 200, 118)).toEqual([0, 136, 204, 255]);
    await page.keyboard.down("Shift");
    await page.mouse.up();
    await page.keyboard.up("Shift");
    expect(await pixel(page, 200, 100)).toEqual([0, 136, 204, 255]);
    expect(await pixel(page, 200, 118)).toEqual([255, 255, 255, 255]);
});

test("Shift makes rectangles square and constrains drawn arrows", async ({
    page,
}) => {
    await open(page);
    await page.getByRole("button", { name: "Rectangle", exact: true }).click();
    await drag(page, [100, 100, 180, 130], true);
    expect(await pixel(page, 150, 180)).not.toEqual([255, 255, 255, 255]);
    expect(await pixel(page, 150, 130)).toEqual([255, 255, 255, 255]);
    await page.getByRole("button", { name: "Arrow", exact: true }).click();
    await drag(page, [100, 100, 200, 160], true);
    expect(await pixel(page, 150, 150)).not.toEqual([255, 255, 255, 255]);
});

test("pipette samples the committed image without creating an edit and Escape cancels it", async ({
    page,
}) => {
    await open(page);
    await page.getByRole("button", { name: "Line", exact: true }).click();
    await page
        .getByRole("button", { name: "Pick color from image", exact: true })
        .click();
    const black = await position(page, 50, 30);
    await page.mouse.click(black.x, black.y);
    await expect(
        page.getByLabel("Custom annotation color", { exact: true })
    ).toHaveValue("#000000");
    await expect(
        page.getByRole("button", { name: "Save image", exact: true })
    ).toBeDisabled();
    await page
        .getByRole("button", { name: "Pick color from image", exact: true })
        .click();
    await page.keyboard.press("Escape");
    await expect(page.locator("canvas")).toBeVisible();
    await expect(
        page.getByRole("button", { name: "Pick color from image", exact: true })
    ).toHaveAttribute("aria-pressed", "false");
});

test("pipette can sample drawn annotations", async ({ page }) => {
    await open(page);
    await page.getByRole("button", { name: "Line", exact: true }).click();
    await page
        .getByLabel("Custom annotation color", { exact: true })
        .fill("#12ab34");
    await drag(page, [100, 100, 200, 100]);
    await page
        .getByLabel("Custom annotation color", { exact: true })
        .fill("#000000");
    await page
        .getByRole("button", { name: "Pick color from image", exact: true })
        .click();
    const sample = await position(page, 150, 100);
    await page.mouse.click(sample.x, sample.y);
    await expect(
        page.getByLabel("Custom annotation color", { exact: true })
    ).toHaveValue("#12ab34");
});

test("markers increment, undo reuses the number, redo preserves it, and clear resets", async ({
    page,
}) => {
    await open(page);
    await page
        .getByRole("button", { name: "Number marker", exact: true })
        .click();
    const first = await position(page, 100, 100);
    await page.mouse.click(first.x, first.y);
    await expect(page.locator(".gw-image-annotator-hint")).toContainText(
        "marker 2"
    );
    const second = await position(page, 180, 100);
    await page.mouse.click(second.x, second.y);
    await expect(page.locator(".gw-image-annotator-hint")).toContainText(
        "marker 3"
    );
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await expect(page.locator(".gw-image-annotator-hint")).toContainText(
        "marker 2"
    );
    await page.getByRole("button", { name: "Redo", exact: true }).click();
    await expect(page.locator(".gw-image-annotator-hint")).toContainText(
        "marker 3"
    );
    await page
        .getByRole("button", { name: "Remove all edits", exact: true })
        .click();
    await expect(page.locator(".gw-image-annotator-hint")).toContainText(
        "marker 1"
    );
    await expect(
        page.getByRole("button", { name: "Save image", exact: true })
    ).toBeDisabled();
});

test("transparent pixels do not silently change the pipette color", async ({
    page,
}) => {
    await open(page, "?transparent");
    await page.getByRole("button", { name: "Line", exact: true }).click();
    await page
        .getByRole("button", { name: "Pick color from image", exact: true })
        .click();
    const clear = await position(page, 100, 100);
    await page.mouse.click(clear.x, clear.y);
    await expect(page.getByRole("alert")).toContainText("visible image pixel");
    await expect(
        page.getByLabel("Custom annotation color", { exact: true })
    ).toHaveValue("#e00000");
    await expect(
        page.getByRole("button", { name: "Pick color from image", exact: true })
    ).toHaveAttribute("aria-pressed", "true");
    await expect(
        page.getByRole("button", { name: "Save image", exact: true })
    ).toBeDisabled();
});

test("Shift preview clears the old draft on transparent images", async ({
    page,
}) => {
    await open(page, "?transparent");
    await page.getByRole("button", { name: "Line", exact: true }).click();
    const start = await position(page, 100, 100),
        end = await position(page, 240, 125);
    await page.mouse.move(start.x, start.y);
    await page.mouse.down();
    await page.mouse.move(end.x, end.y);
    expect((await pixel(page, 200, 118))[3]).toBe(255);
    await page.keyboard.down("Shift");
    expect((await pixel(page, 200, 118))[3]).toBe(0);
    expect((await pixel(page, 200, 100))[3]).toBe(255);
    await page.keyboard.press("Escape");
    await page.mouse.up();
    await page.keyboard.up("Shift");
    expect((await pixel(page, 200, 100))[3]).toBe(0);
    await expect(
        page.getByRole("button", { name: "Save image", exact: true })
    ).toBeDisabled();
});

test("cancelled marker gestures do not consume a number", async ({ page }) => {
    await open(page);
    await page
        .getByRole("button", { name: "Number marker", exact: true })
        .click();
    const center = await position(page, 100, 100);
    await page.mouse.move(center.x, center.y);
    await page.mouse.down();
    await page
        .locator("canvas")
        .dispatchEvent("pointercancel", { pointerId: 1, bubbles: true });
    await page.mouse.up();
    await expect(page.locator(".gw-image-annotator-hint")).toContainText(
        "marker 1"
    );
    await expect(
        page.getByRole("button", { name: "Save image", exact: true })
    ).toBeDisabled();
    const edge = await position(page, 0, 0);
    await page.mouse.click(edge.x + 0.1, edge.y + 0.1);
    await expect(page.locator(".gw-image-annotator-hint")).toContainText(
        "marker 2"
    );
    expect(await pixel(page, 20, 12)).toEqual([224, 0, 0, 255]);
});

test("custom colors and markers remain locked during saving", async ({
    page,
}) => {
    await open(page);
    await page
        .getByRole("button", { name: "Number marker", exact: true })
        .click();
    const center = await position(page, 100, 100);
    await page.mouse.click(center.x, center.y);
    await page.evaluate(() => {
        window.imageEditorTest.saveMode = "pending";
    });
    await page.getByRole("button", { name: "Save image", exact: true }).click();
    await expect(
        page.getByLabel("Custom annotation color", { exact: true })
    ).toBeDisabled();
    await expect(
        page.getByLabel("Annotation color hex", { exact: true })
    ).toBeDisabled();
    await expect(
        page.getByRole("button", { name: "Pick color from image", exact: true })
    ).toBeDisabled();
    await expect(
        page.getByRole("button", { name: "Number marker", exact: true })
    ).toBeDisabled();
    await page.evaluate(() => window.imageEditorTest.releaseSave());
    await expect(page.getByLabel("Saved image dimensions")).toHaveText(
        "400 × 300"
    );
});
