import { expect, Page, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

type CanvasMemoryProbe = {
    canvases: HTMLCanvasElement[];
    exports: HTMLCanvasElement[];
    initial: HTMLCanvasElement[];
    working: HTMLCanvasElement[];
    visible: HTMLCanvasElement | null;
    committed: HTMLCanvasElement | null;
    losslessExports: {
        width: number;
        height: number;
        sameEveryPixel: boolean;
        mime: string;
    }[];
};

declare global {
    interface Window {
        canvasMemoryProbe: CanvasMemoryProbe;
    }
}

const rendererPath =
    "/@fs" +
    fileURLToPath(
        new URL("../../src/frontend/image_annotator/render.ts", import.meta.url)
    );

test("reusing a full-resolution render preserves transparency and removes undone strokes", async ({
    page,
}) => {
    await page.goto("/");
    const result = await page.evaluate(async (modulePath) => {
        const { renderImage, cropCanvas } = (await import(
            modulePath
        )) as typeof import("../../src/frontend/image_annotator/render");
        const source = document.createElement("canvas");
        source.width = 641;
        source.height = 421;
        const context = source.getContext("2d")!;
        const pixels = context.createImageData(source.width, source.height);
        for (let y = 0; y < source.height; y++)
            for (let x = 0; x < source.width; x++) {
                const offset = (y * source.width + x) * 4;
                pixels.data.set(
                    [x % 256, y % 256, (x + y) % 256, x % 3 ? 255 : 0],
                    offset
                );
            }
        context.putImageData(pixels, 0, 0);
        const image = new Image();
        image.src = source.toDataURL();
        await image.decode();
        const line = {
            kind: "line" as const,
            color: "#ff0000",
            width: 1,
            x0: 10,
            y0: 10,
            x1: 500,
            y1: 310,
        };
        const working = renderImage(image, [line]);
        let sameEveryPixel = true;
        for (const ops of [[], [line], []]) {
            const reused = renderImage(image, ops, false, working);
            const fresh = renderImage(image, ops);
            const a = reused
                .getContext("2d")!
                .getImageData(0, 0, 641, 421).data;
            const b = fresh.getContext("2d")!.getImageData(0, 0, 641, 421).data;
            sameEveryPixel &&= a.every((value, i) => value === b[i]);
            if (reused !== working) throw new Error("Working canvas replaced");
        }
        const crop = { x0: 7, y0: 9, x1: 600, y1: 400 };
        const copy = cropCanvas(working, crop);
        const copied = copy
            .getContext("2d")!
            .getImageData(0, 0, copy.width, copy.height).data;
        const expected = working
            .getContext("2d")!
            .getImageData(7, 9, 593, 391).data;
        return {
            width: working.width,
            height: working.height,
            sameEveryPixel,
            cropSize: [copy.width, copy.height],
            cropSameEveryPixel: copied.every(
                (value, i) => value === expected[i]
            ),
        };
    }, rendererPath);
    expect(result).toEqual({
        width: 641,
        height: 421,
        sameEveryPixel: true,
        cropSize: [593, 391],
        cropSameEveryPixel: true,
    });
});

async function trackCanvases(page: Page) {
    await page.addInitScript(() => {
        const original = document.createElement.bind(document);
        const probe: CanvasMemoryProbe = {
            canvases: [],
            exports: [],
            initial: [],
            working: [],
            visible: null,
            committed: null,
            losslessExports: [],
        };
        Object.assign(window, { canvasMemoryProbe: probe });
        document.createElement = ((...args: Parameters<typeof original>) => {
            const element = original(...args);
            if (element instanceof HTMLCanvasElement)
                probe.canvases.push(element);
            return element;
        }) as typeof document.createElement;
        const toBlob = HTMLCanvasElement.prototype.toBlob;
        HTMLCanvasElement.prototype.toBlob = function (
            callback,
            type,
            quality
        ) {
            probe.exports.push(this);
            const { width, height } = this;
            const expected = this.getContext("2d")!.getImageData(
                0,
                0,
                width,
                height
            ).data;
            return toBlob.call(
                this,
                async (blob) => {
                    if (blob) {
                        const bitmap = await createImageBitmap(blob);
                        const decoded = original("canvas");
                        decoded.width = bitmap.width;
                        decoded.height = bitmap.height;
                        const context = decoded.getContext("2d")!;
                        context.drawImage(bitmap, 0, 0);
                        const actual = context.getImageData(
                            0,
                            0,
                            width,
                            height
                        ).data;
                        probe.losslessExports.push({
                            width: bitmap.width,
                            height: bitmap.height,
                            sameEveryPixel: actual.every(
                                (value, i) => value === expected[i]
                            ),
                            mime: blob.type,
                        });
                        bitmap.close();
                        decoded.width = decoded.height = 0;
                    }
                    callback(blob);
                },
                type,
                quality
            );
        };
    });
}

async function draw(page: Page) {
    const canvas = page.locator("canvas");
    const box = (await canvas.boundingBox())!;
    await page.mouse.move(box.x + box.width * 0.1, box.y + box.height * 0.1);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.6);
    await page.mouse.up();
}

for (const crop of [false, true])
    test(`${crop ? "cropped" : "full-resolution"} export reuses the committed layer and releases buffers`, async ({
        page,
    }) => {
        await trackCanvases(page);
        await page.goto("/");
        await expect(page.locator("canvas")).toHaveAttribute("width", "400");
        await page.evaluate(() => {
            const probe = window.canvasMemoryProbe;
            probe.initial = [...probe.canvases];
            probe.visible = document.querySelector("canvas");
            probe.committed =
                probe.canvases.find(
                    (canvas: HTMLCanvasElement) =>
                        canvas !== probe.visible &&
                        !canvas.isConnected &&
                        canvas.width === 400 &&
                        canvas.height === 300 &&
                        canvas !== probe.canvases[0]
                ) ?? null;
            if (!probe.committed) throw new Error("Missing committed canvas");
        });
        await page.getByRole("button", { name: "Line", exact: true }).click();
        await draw(page);
        await page.getByRole("button", { name: "Undo", exact: true }).click();
        await page.getByRole("button", { name: "Redo", exact: true }).click();
        expect(
            await page.evaluate(() => {
                const probe = window.canvasMemoryProbe;
                return probe.canvases.length - probe.initial.length;
            })
        ).toBe(0);
        if (crop) {
            await page
                .getByRole("button", { name: "Crop", exact: true })
                .click();
            await draw(page);
        }
        await page
            .getByRole("button", { name: "Save image", exact: true })
            .click();
        await expect(page.getByRole("dialog")).toHaveCount(0);
        const result = await page.evaluate(() => {
            const probe = window.canvasMemoryProbe;
            if (!probe.visible || !probe.committed)
                throw new Error("Missing working canvases");
            return {
                exportedCommitted: probe.exports[0] === probe.committed,
                exportedReleased:
                    probe.exports[0].width === 0 &&
                    probe.exports[0].height === 0,
                visibleReleased:
                    probe.visible.width === 0 && probe.visible.height === 0,
                committedReleased:
                    probe.committed.width === 0 && probe.committed.height === 0,
                saved: window.imageEditorTest.saved,
                losslessExports: probe.losslessExports,
            };
        });
        expect(result.exportedCommitted).toBe(!crop);
        expect(result.exportedReleased).toBe(true);
        expect(result.visibleReleased).toBe(true);
        expect(result.committedReleased).toBe(true);
        expect(result.losslessExports).toHaveLength(1);
        expect(result.losslessExports[0].sameEveryPixel).toBe(true);
        expect(result.losslessExports[0].mime).toBe("image/png");
        expect(result.losslessExports[0].width).toBe(result.saved?.width);
        expect(result.losslessExports[0].height).toBe(result.saved?.height);
        if (!crop) {
            expect(result.saved?.width).toBe(400);
            expect(result.saved?.height).toBe(300);
        }
    });

test("Cancel releases full-size pixel buffers without exporting", async ({
    page,
}) => {
    await trackCanvases(page);
    await page.goto("/");
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await page.evaluate(() => {
        window.canvasMemoryProbe.working =
            window.canvasMemoryProbe.canvases.slice(1);
    });
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    const result = await page.evaluate(() => {
        const probe = window.canvasMemoryProbe;
        return {
            exported: probe.exports.length,
            released: probe.working.every(
                (canvas: HTMLCanvasElement) =>
                    canvas.width === 0 && canvas.height === 0
            ),
        };
    });
    expect(result).toEqual({ exported: 0, released: true });
});

test("failed cropped save releases the export copy and preserves the editable source for retry", async ({
    page,
}) => {
    await trackCanvases(page);
    await page.goto("/");
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await page.getByRole("button", { name: "Crop", exact: true }).click();
    await draw(page);
    await page.evaluate(() => {
        window.imageEditorTest.saveMode = "reject";
    });
    await page.getByRole("button", { name: "Save image", exact: true }).click();
    await expect(page.getByRole("alert")).toHaveText("Simulated save failed");
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    expect(
        await page.evaluate(() => {
            const copy = window.canvasMemoryProbe.exports[0];
            return [copy.width, copy.height];
        })
    ).toEqual([0, 0]);
    await page.evaluate(() => {
        window.imageEditorTest.saveMode = "success";
    });
    await page.getByRole("button", { name: "Save image", exact: true }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    const exports = await page.evaluate(
        () => window.canvasMemoryProbe.losslessExports
    );
    expect(exports).toHaveLength(2);
    expect(exports.every((output) => output.sameEveryPixel)).toBe(true);
    expect(exports[0]).toEqual(exports[1]);
});
