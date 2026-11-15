import { expect, test, Page } from "@playwright/test";
import type { AnnotationOp } from "../../src/frontend/image_annotator/render";

test.beforeEach(async ({ page }) => {
    page.on("response", (response) => {
        if (
            ["stylesheet", "script", "font"].includes(
                response.request().resourceType()
            )
        ) {
            expect(
                response.status(),
                `Local asset ${response.url()}`
            ).toBeLessThan(400);
            if (
                response.request().resourceType() === "stylesheet" &&
                response.status() !== 304
            ) {
                expect(
                    response.headers()["content-type"],
                    `Stylesheet ${response.url()}`
                ).toContain("css");
            }
        }
    });
});

async function open(page: Page) {
    await page.goto("/");
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
}
async function region(page: Page, coordinates = [50, 20, 250, 220]) {
    const canvas = page.locator("canvas");
    const box = (await canvas.boundingBox())!;
    const dimensions = await canvas.evaluate((node: HTMLCanvasElement) => ({
        width: node.width,
        height: node.height,
    }));
    const [x0, y0, x1, y1] = coordinates;
    await page.mouse.move(
        box.x + (x0 * box.width) / dimensions.width,
        box.y + (y0 * box.height) / dimensions.height
    );
    await page.mouse.down();
    await page.mouse.move(
        box.x + (x1 * box.width) / dimensions.width,
        box.y + (y1 * box.height) / dimensions.height
    );
    await page.mouse.up();
}

test("pixelate replaces transparent source pixels with an opaque synthetic mosaic", async ({
    page,
}) => {
    await open(page);
    const result = await page.evaluate(() =>
        window.imageEditorTest.render(
            [{ kind: "pixelate", x0: 40, y0: 10, x1: 80, y1: 90 }],
            true
        )
    );
    expect(result.stroke[3]).toBe(255);
    expect(result.adjacent[3]).toBe(255);
    await expect(
        page.getByRole("button", { name: "Blur", exact: true })
    ).toHaveCount(0);
});

test("black boxes flatten to opaque pixels on transparent images", async ({
    page,
}) => {
    await open(page);
    const result = await page.evaluate(() =>
        window.imageEditorTest.render(
            [{ kind: "blackout", x0: 40, y0: 10, x1: 80, y1: 90 }],
            true
        )
    );
    expect(result.stroke).toEqual([0, 0, 0, 255]);
    expect(result.adjacent).toEqual([0, 0, 0, 255]);
});

for (const [name, coordinates, expected] of [
    ["forward", [40, 10, 80, 90], [40, 80]],
    ["reverse", [80, 90, 40, 10], [40, 80]],
    ["clamped", [-20, -10, 250, 120], [200, 100]],
    ["fractional", [40.2, 10.2, 79.8, 89.8], [40, 80]],
] as const) {
    test(`crop exports correct ${name} dimensions`, async ({ page }) => {
        await open(page);
        const [x0, y0, x1, y1] = coordinates;
        const result = await page.evaluate(
            (op) => window.imageEditorTest.render([op]),
            { kind: "crop", x0, y0, x1, y1 } as AnnotationOp
        );
        expect([result.width, result.height]).toEqual(expected);
    });
}

for (const coordinates of [
    [100, 20, 100, 90],
    [20, 50, 90, 50],
    [250, 120, 300, 150],
]) {
    test(`invalid crop ${coordinates.join(",")} cannot export the source`, async ({
        page,
    }) => {
        await open(page);
        const [x0, y0, x1, y1] = coordinates;
        await expect(
            page.evaluate((op) => window.imageEditorTest.render([op]), {
                kind: "crop",
                x0,
                y0,
                x1,
                y1,
            } as AnnotationOp)
        ).rejects.toThrow();
    });
}

test("zero-width pointer crop leaves save disabled", async ({ page }) => {
    await open(page);
    await page.getByRole("button", { name: "Crop", exact: true }).click();
    const box = (await page.locator("canvas").boundingBox())!;
    await page.mouse.move(box.x + 100, box.y + 50);
    await page.mouse.down();
    await page.mouse.move(box.x + 100, box.y + 200);
    await page.mouse.up();
    await expect(
        page.getByRole("button", { name: "Save image", exact: true })
    ).toBeDisabled();
    await expect(page.getByRole("alert")).toBeVisible();
});

test("pointer selection, undo, redo, and exported crop", async ({ page }) => {
    await open(page);
    await page.getByRole("button", { name: "Crop", exact: true }).focus();
    await page.keyboard.press("Enter");
    await region(page);
    await page.getByRole("button", { name: /^Undo/ }).click();
    await expect(
        page.getByRole("button", { name: "Save image", exact: true })
    ).toBeDisabled();
    await page.getByRole("button", { name: /^Redo/ }).click();
    await page.getByRole("button", { name: "Save image", exact: true }).click();
    await expect(page.getByLabel("Saved image dimensions")).toHaveText(
        "200 × 200"
    );
});

test("saving freezes history, tools, drawing, and dismissal", async ({
    page,
}) => {
    await open(page);
    await region(page, [40, 10, 80, 90]);
    await page.evaluate(() => {
        window.imageEditorTest.saveMode = "pending";
    });
    await page.getByRole("button", { name: "Save image", exact: true }).click();
    await expect(page.getByRole("button", { name: /^Undo/ })).toBeDisabled();
    await expect(
        page.getByRole("button", { name: "Crop", exact: true })
    ).toBeDisabled();
    await region(page, [100, 100, 200, 200]);
    await expect(
        page.getByRole("button", { name: "Cancel", exact: true })
    ).toBeDisabled();
    await page.keyboard.press("Control+z");
    await page.keyboard.press("Escape");
    await expect(page.locator("canvas")).toBeVisible();
    await page.evaluate(() => window.imageEditorTest.releaseSave());
    await expect(page.getByLabel("Saved image dimensions")).toHaveText(
        "400 × 300"
    );
});

test("save failure and a later source poll do not apply edits twice", async ({
    page,
}) => {
    await open(page);
    await page.getByRole("button", { name: "Crop", exact: true }).click();
    await region(page);
    await page.evaluate(() => {
        window.imageEditorTest.saveMode = "reject";
    });
    await page.getByRole("button", { name: "Save image", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText(
        "Simulated save failed"
    );
    await page.evaluate(() => {
        window.imageEditorTest.source(200, 200);
        window.imageEditorTest.saveMode = "success";
    });
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await page.getByRole("button", { name: "Save image", exact: true }).click();
    await expect(page.getByLabel("Saved image dimensions")).toHaveText(
        "200 × 200"
    );
});

for (const theme of ["light", "dark"]) {
    for (const width of [1440, 1024, 768, 390]) {
        test(`editor works offline at ${width}px in ${theme} theme`, async ({
            page,
        }, testInfo) => {
            const external: string[] = [];
            page.on("request", (request) => {
                if (
                    /^https?:/.test(request.url()) &&
                    !request.url().startsWith("http://127.0.0.1:4178")
                )
                    external.push(request.url());
            });
            await page.setViewportSize({ width, height: 900 });
            await page.emulateMedia({ reducedMotion: "reduce" });
            await open(page);
            await page.evaluate((theme) => {
                document.documentElement.dataset.theme = theme;
                document.documentElement.dataset.bsTheme = theme;
            }, theme);
            await expect(
                page.getByText("Set selection coordinates", { exact: true })
            ).toHaveCount(0);
            const bounds = await page
                .locator(".ReactModal__Content")
                .boundingBox();
            expect(bounds!.x).toBeGreaterThanOrEqual(0);
            expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width + 1);
            expect(
                await page.evaluate(
                    () => document.documentElement.scrollWidth <= innerWidth
                )
            ).toBe(true);
            await region(page, [0, 0, 80, 90]);
            await expect(
                page.getByRole("button", { name: "Save image", exact: true })
            ).toBeEnabled();
            expect(external).toEqual([]);
            await testInfo.attach(`editor-${theme}-${width}`, {
                body: await page.screenshot(),
                contentType: "image/png",
            });
        });
    }
}

test("edited pixels are uploaded instead of the selected original", async ({
    page,
}) => {
    await page.goto("/?upload");
    const dataUrl = await page.evaluate(() => window.imageEditorTest.fixture());
    await page.locator('input[type="file"]').setInputFiles({
        name: "proof.png",
        mimeType: "image/png",
        buffer: Buffer.from(dataUrl.split(",")[1], "base64"),
    });
    await page
        .getByLabel("Friendly name", { exact: true })
        .fill("Cropped proof");
    await page
        .getByLabel("Caption", { exact: true })
        .fill("Only the selected region");
    await page
        .getByRole("button", { name: "Edit image before uploading" })
        .click();
    await page.getByRole("button", { name: "Crop", exact: true }).click();
    await region(page, [40, 10, 80, 90]);
    await page
        .getByRole("button", { name: "Use edited image", exact: true })
        .click();
    await expect
        .poll(() =>
            page
                .getByAltText("Selected evidence preview", { exact: true })
                .evaluate((img: HTMLImageElement) => [
                    img.naturalWidth,
                    img.naturalHeight,
                ])
        )
        .toEqual([40, 80]);
    let dimensions: number[] = [];
    await page.route("**/test-upload", async (route) => {
        const request = route.request();
        expect(request.headers()["x-csrftoken"]).toBe("fixture-csrf-token");
        const form = await new Response(
            new Uint8Array(request.postDataBuffer()!),
            {
                headers: { "content-type": request.headers()["content-type"] },
            }
        ).formData();
        expect(form.get("friendly_name")).toBe("Cropped proof");
        const file = form.get("document") as File;
        expect(file.type).toBe("image/png");
        const bytes = Buffer.from(await file.arrayBuffer());
        dimensions = [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
        await route.fulfill({ json: { pk: 42 } });
    });
    await page
        .getByRole("button", { name: "Upload and insert", exact: true })
        .click();
    await expect
        .poll(() => page.evaluate(() => window.imageEditorTest.uploaded))
        .toBe(42);
    expect(dimensions).toEqual([40, 80]);
});

test("cancel editing leaves the original selected file intact", async ({
    page,
}) => {
    await page.goto("/?upload");
    const dataUrl = await page.evaluate(() => window.imageEditorTest.fixture());
    await page.locator('input[type="file"]').setInputFiles({
        name: "proof.png",
        mimeType: "image/png",
        buffer: Buffer.from(dataUrl.split(",")[1], "base64"),
    });
    await page
        .getByRole("button", { name: "Edit image before uploading" })
        .click();
    await page.getByRole("button", { name: "Crop", exact: true }).click();
    await region(page);
    await page
        .getByRole("dialog")
        .getByRole("button", { name: "Cancel", exact: true })
        .click();
    const file = await page
        .locator('input[type="file"]')
        .evaluate(async (input: HTMLInputElement) => {
            const file = input.files![0];
            const bitmap = await createImageBitmap(file);
            return {
                name: file.name,
                width: bitmap.width,
                height: bitmap.height,
            };
        });
    expect(file).toEqual({ name: "proof.png", width: 400, height: 300 });
});

for (const [name, response, message] of [
    [
        "HTML login page",
        { status: 200, contentType: "text/html", body: "<html>Sign in</html>" },
        "session may have expired",
    ],
    ["expired session", { status: 401, json: {} }, "session may have expired"],
    [
        "stale revision",
        {
            status: 409,
            json: { document: ["This image changed while you were editing."] },
        },
        "image changed",
    ],
    ["large upload", { status: 413, json: {} }, "upload limit"],
    ["storage outage", { status: 503, json: {} }, "retry saving"],
] as const) {
    test(`mutation transport rejects ${name} without claiming success`, async ({
        page,
    }) => {
        await open(page);
        await page.route("**/test-change", (route) => route.fulfill(response));
        const result = await page.evaluate(async () => {
            try {
                await window.imageEditorTest.change("/test-change");
                return "SAVED";
            } catch (error) {
                return (error as Error).message;
            }
        });
        expect(result.toLowerCase()).toContain(message);
    });
}

test("mutation transport requires a JSON confirmation and preserves CSRF", async ({
    page,
}) => {
    await open(page);
    await page.route("**/test-change", async (route) => {
        expect(route.request().headers()["x-csrftoken"]).toBe(
            "fixture-csrf-token"
        );
        await route.fulfill({ json: { pk: 1 } });
    });
    await expect(
        page.evaluate(() => window.imageEditorTest.change("/test-change"))
    ).resolves.toBeUndefined();
});

test("existing evidence controls appear when collaboration becomes editable", async ({
    page,
}) => {
    await page.goto("/?evidence");
    await expect(
        page.getByText("Existing caption", { exact: false })
    ).toBeVisible();
    await expect(
        page.getByRole("button", { name: "Edit image", exact: true })
    ).toHaveCount(0);
    await page.evaluate(() => window.imageEditorTest.connected());
    await expect(
        page.getByRole("button", { name: "Edit image", exact: true })
    ).toBeVisible();
    await expect(
        page.getByRole("button", { name: /Report size:/ })
    ).toBeVisible();
});

for (const width of [1440, 390]) {
    test(`large image selection stays reachable at ${width}px`, async ({
        page,
    }) => {
        await page.setViewportSize({ width, height: 640 });
        await page.goto("/?large");
        await expect(page.locator("canvas")).toHaveAttribute("width", "800");
        await expect(
            page.getByText("Set selection coordinates", { exact: true })
        ).toHaveCount(0);
        await region(page, [0, 0, 100, 100]);
        await expect(
            page.getByRole("button", { name: "Save image", exact: true })
        ).toBeEnabled();
        const modal = await page.locator(".ReactModal__Content").boundingBox();
        const save = await page
            .getByRole("button", { name: "Save image", exact: true })
            .boundingBox();
        expect(save!.y + save!.height).toBeLessThanOrEqual(
            modal!.y + modal!.height
        );
        expect(save!.y + save!.height).toBeLessThanOrEqual(640);
    });
}

test("retry after signing in uses the rotated CSRF token", async ({
    page,
    context,
}) => {
    await open(page);
    const rotatedToken = "A".repeat(32);
    await context.addCookies([
        {
            name: "csrftoken",
            value: rotatedToken,
            url: "http://127.0.0.1:4178",
        },
    ]);
    await page.route("**/test-change", async (route) => {
        expect(route.request().headers()["x-csrftoken"]).toBe(rotatedToken);
        await route.fulfill({ json: { pk: 1 } });
    });
    await expect(
        page.evaluate(() => window.imageEditorTest.change("/test-change"))
    ).resolves.toBeUndefined();
});

test("pasting screenshots with the same filename updates the preview and uploaded file", async ({
    page,
}) => {
    await page.goto("/?upload");
    async function paste(width: number, height: number) {
        await page.getByLabel("Friendly name", { exact: true }).focus();
        await page.evaluate(
            async ({ width, height }) => {
                const canvas = document.createElement("canvas");
                canvas.width = width;
                canvas.height = height;
                const blob = await new Promise<Blob>((resolve) =>
                    canvas.toBlob((blob) => resolve(blob!), "image/png")
                );
                const clipboard = new DataTransfer();
                clipboard.items.add(
                    new File([blob], "image.png", { type: "image/png" })
                );
                document.activeElement!.dispatchEvent(
                    new ClipboardEvent("paste", {
                        clipboardData: clipboard,
                        bubbles: true,
                        cancelable: true,
                    })
                );
            },
            { width, height }
        );
    }
    const preview = page.getByAltText("Selected evidence preview", {
        exact: true,
    });
    await paste(120, 80);
    await expect(preview).toBeVisible();
    await expect
        .poll(() =>
            preview.evaluate((img: HTMLImageElement) => [
                img.naturalWidth,
                img.naturalHeight,
            ])
        )
        .toEqual([120, 80]);
    const firstUrl = await preview.getAttribute("src");
    await paste(240, 160);
    await expect(preview).not.toHaveAttribute("src", firstUrl!);
    await expect
        .poll(() =>
            preview.evaluate((img: HTMLImageElement) => [
                img.naturalWidth,
                img.naturalHeight,
            ])
        )
        .toEqual([240, 160]);
    await expect(
        page.getByRole("button", { name: "Edit image before uploading" })
    ).toBeVisible();
    expect(
        await page
            .locator('input[type="file"]')
            .evaluate(async (input: HTMLInputElement) => {
                const bitmap = await createImageBitmap(input.files![0]);
                const dimensions = [bitmap.width, bitmap.height];
                bitmap.close();
                return dimensions;
            })
    ).toEqual([240, 160]);
    await page
        .getByLabel("Friendly name", { exact: true })
        .fill("Pasted screenshot");
    await page.getByLabel("Caption", { exact: true }).fill("Latest paste");
    await page.route("**/test-upload", async (route) => {
        const request = route.request();
        const form = await new Response(
            new Uint8Array(request.postDataBuffer()!),
            { headers: { "content-type": request.headers()["content-type"] } }
        ).formData();
        const bytes = Buffer.from(
            await (form.get("document") as File).arrayBuffer()
        );
        expect([bytes.readUInt32BE(16), bytes.readUInt32BE(20)]).toEqual([
            240, 160,
        ]);
        await route.fulfill({ json: { pk: 43 } });
    });
    await page
        .getByRole("button", { name: "Upload and insert", exact: true })
        .click();
    await expect
        .poll(() => page.evaluate(() => window.imageEditorTest.uploaded))
        .toBe(43);
});

test("evidence edit page stages image edits without submitting other fields", async ({
    page,
}) => {
    await page.goto("/?evidence-page");
    await page.getByLabel("Caption", { exact: true }).fill("Unsaved caption");
    await page
        .getByRole("button", { name: "Edit evidence image", exact: true })
        .click();
    await expect(
        page.getByText(/everywhere this evidence is used/)
    ).toBeVisible();
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await page.getByRole("button", { name: "Crop", exact: true }).click();
    await region(page, [50, 20, 250, 220]);
    await page
        .getByRole("button", { name: "Use edited image", exact: true })
        .click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByRole("status")).toContainText("Use Save Changes");
    await expect(page.getByLabel("Caption", { exact: true })).toHaveValue(
        "Unsaved caption"
    );
    expect(
        await page
            .locator('input[type="file"]')
            .evaluate(async (input: HTMLInputElement) => {
                const image = await createImageBitmap(input.files![0]);
                const result = {
                    name: input.files![0].name,
                    width: image.width,
                    height: image.height,
                };
                image.close();
                return result;
            })
    ).toEqual({ name: "proof.png", width: 200, height: 200 });
    await page
        .getByRole("button", { name: "Edit evidence image", exact: true })
        .click();
    await expect(page.locator("canvas")).toHaveAttribute("width", "200");
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(page.getByLabel("Caption", { exact: true })).toHaveValue(
        "Unsaved caption"
    );
});

test("evidence edit page cancellation preserves its file and follows replacement changes", async ({
    page,
}) => {
    await page.goto("/?evidence-page");
    await page
        .getByRole("button", { name: "Edit evidence image", exact: true })
        .click();
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await region(page);
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    expect(
        await page
            .locator('input[type="file"]')
            .evaluate((input: HTMLInputElement) => input.files!.length)
    ).toBe(0);
    await page.locator('input[type="file"]').setInputFiles({
        name: "notes.txt",
        mimeType: "text/plain",
        buffer: Buffer.from("notes"),
    });
    await expect(
        page.getByRole("button", { name: "Edit evidence image", exact: true })
    ).toHaveCount(0);
    const dataUrl = await page.evaluate(() => window.imageEditorTest.fixture());
    await page.locator('input[type="file"]').setInputFiles({
        name: "replacement.png",
        mimeType: "image/png",
        buffer: Buffer.from(dataUrl.split(",")[1], "base64"),
    });
    await page
        .getByRole("button", { name: "Edit evidence image", exact: true })
        .click();
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await region(page);
    await page
        .getByRole("button", { name: "Use edited image", exact: true })
        .click();
    expect(
        await page
            .locator('input[type="file"]')
            .evaluate((input: HTMLInputElement) => input.files![0].name)
    ).toBe("replacement.png");
});

test("pixelate preview, undo/redo, and pre-upload PNG have identical pixels", async ({
    page,
}) => {
    await page.goto("/?upload");
    const source = await page.evaluate(() => window.imageEditorTest.fixture());
    await page.locator('input[type="file"]').setInputFiles({
        name: "proof.png",
        mimeType: "image/png",
        buffer: Buffer.from(source.split(",")[1], "base64"),
    });
    await page
        .getByRole("button", { name: "Edit image before uploading" })
        .click();
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await page.getByRole("button", { name: "Pixelate", exact: true }).click();
    await region(page, [40, 10, 80, 90]);
    const preview = await page
        .locator("canvas")
        .evaluate((canvas: HTMLCanvasElement) => canvas.toDataURL());
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await expect(
        page.getByRole("button", { name: "Use edited image", exact: true })
    ).toBeDisabled();
    await page.getByRole("button", { name: "Redo", exact: true }).click();
    expect(
        await page
            .locator("canvas")
            .evaluate((canvas: HTMLCanvasElement) => canvas.toDataURL())
    ).toBe(preview);
    await page
        .getByRole("button", { name: "Use edited image", exact: true })
        .click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    const saved = await page
        .locator('input[type="file"]')
        .evaluate(async (input: HTMLInputElement) => {
            const image = await createImageBitmap(input.files![0]);
            const canvas = document.createElement("canvas");
            canvas.width = image.width;
            canvas.height = image.height;
            canvas.getContext("2d")!.drawImage(image, 0, 0);
            image.close();
            return canvas.toDataURL();
        });
    expect(saved).toBe(preview);
});

test("Pixelate offers border blending by default and a neutral option for new selections", async ({
    page,
}) => {
    await open(page);
    await page.getByRole("button", { name: "Pixelate", exact: true }).click();
    const colors = page.getByLabel("Pixelate colors", { exact: true });
    await expect(colors).toHaveValue("border");
    await region(page, [100, 100, 180, 180]);
    const bright = await page
        .locator("canvas")
        .evaluate(
            (canvas: HTMLCanvasElement) =>
                canvas.getContext("2d")!.getImageData(140, 140, 1, 1).data[0]
        );
    expect(bright).toBeGreaterThan(230);
    await colors.selectOption("neutral");
    await region(page, [200, 100, 280, 180]);
    const neutral = await page
        .locator("canvas")
        .evaluate((canvas: HTMLCanvasElement) => [
            ...canvas.getContext("2d")!.getImageData(240, 140, 1, 1).data,
        ]);
    expect(neutral[0]).toBeLessThan(160);
    expect(neutral[3]).toBe(255);
});

test("placed pixelations retain their colors through later drafts, crop, and undo/redo", async ({
    page,
}) => {
    await page.goto("/?upload");
    const source = await page.evaluate(() => {
        const canvas = document.createElement("canvas");
        canvas.width = 400;
        canvas.height = 300;
        const ctx = canvas.getContext("2d")!;
        const pixels = ctx.createImageData(400, 300);
        for (let y = 0; y < 300; y++)
            for (let x = 0; x < 400; x++) {
                const i = (y * 400 + x) * 4,
                    value = (x + y) % 2 ? 255 : 0;
                pixels.data.set([value, value, value, 255], i);
            }
        ctx.putImageData(pixels, 0, 0);
        ctx.fillStyle = "white";
        ctx.fillRect(98, 97, 104, 7);
        ctx.fillStyle = "black";
        ctx.fillRect(90, 158, 40, 6);
        return canvas.toDataURL();
    });
    await page.locator('input[type="file"]').setInputFiles({
        name: "palette.png",
        mimeType: "image/png",
        buffer: Buffer.from(source.split(",")[1], "base64"),
    });
    await page
        .getByRole("button", { name: "Edit image before uploading" })
        .click();
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await page.locator("canvas").evaluate((canvas: HTMLCanvasElement) => {
        canvas.style.width = "400px";
        canvas.style.height = "300px";
    });
    await page.getByRole("button", { name: "Pixelate", exact: true }).click();
    await region(page, [100, 100, 200, 160]);
    const sample = () =>
        page
            .locator("canvas")
            .evaluate((canvas: HTMLCanvasElement) => [
                ...canvas.getContext("2d")!.getImageData(155, 145, 1, 1).data,
            ]);
    const before = await sample();
    const box = (await page.locator("canvas").boundingBox())!;
    await page.mouse.move(
        box.x + (box.width * 98) / 400,
        box.y + (box.height * 97) / 300
    );
    await page.mouse.down();
    await page.mouse.move(
        box.x + (box.width * 202) / 400,
        box.y + (box.height * 104) / 300
    );
    const draft = await sample();
    expect(draft).toEqual(before);
    await page.mouse.up();
    await expect.poll(sample).toEqual(before);
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await expect.poll(sample).toEqual(before);
    await page.getByRole("button", { name: "Redo", exact: true }).click();
    await expect.poll(sample).toEqual(before);
    await page.getByRole("button", { name: "Crop", exact: true }).click();
    await region(page, [90, 90, 220, 180]);
    await expect.poll(sample).toEqual(before);
    await page.evaluate(
        () => (document.documentElement.dataset.theme = "dark")
    );
    await page.setViewportSize({ width: 1024, height: 900 });
    await expect.poll(sample).toEqual(before);
});

test("a new four-border gradient has identical colors before and after placement beside an existing mark", async ({
    page,
}) => {
    await open(page);
    await region(page, [100, 100, 200, 200]); // Opaque black box, visible on the next selection's left border.
    await page.getByRole("button", { name: "Pixelate", exact: true }).click();
    const box = (await page.locator("canvas").boundingBox())!;
    await page.mouse.move(
        box.x + (box.width * 200) / 400,
        box.y + (box.height * 120) / 300
    );
    await page.mouse.down();
    await page.mouse.move(
        box.x + (box.width * 280) / 400,
        box.y + (box.height * 180) / 300
    );
    const sample = () =>
        page
            .locator("canvas")
            .evaluate((canvas: HTMLCanvasElement) => [
                ...canvas.getContext("2d")!.getImageData(206, 150, 1, 1).data,
            ]);
    const preview = await sample();
    expect(preview[0]).toBeLessThan(100);
    expect(preview[3]).toBe(255);
    await page.mouse.up();
    await expect.poll(sample).toEqual(preview);
});
