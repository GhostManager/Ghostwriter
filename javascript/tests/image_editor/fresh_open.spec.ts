import { expect, Page, test } from "@playwright/test";

const metadata = (document = "current.png") => [
    {
        id: 1,
        friendlyName: "Current evidence",
        caption: "Current caption",
        document,
    },
];

async function image(page: Page, width = 600, height = 350) {
    const data = await page.evaluate(
        ({ width, height }) => {
            const canvas = document.createElement("canvas");
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext("2d")!;
            ctx.fillStyle = "#6d70a7";
            ctx.fillRect(0, 0, width, height);
            return canvas.toDataURL("image/png").split(",")[1];
        },
        { width, height }
    );
    return Buffer.from(data, "base64");
}

async function initial(page: Page) {
    await page.route("**/reporting/evidence/download/1?*", async (route) => {
        await route.fulfill({
            contentType: "image/png",
            body: await image(page, 400, 300),
        });
    });
    await page.goto("/?fresh-open");
    await expect(
        page.getByRole("button", { name: "Edit image", exact: true })
    ).toBeEnabled();
}

async function open(page: Page) {
    await page.getByRole("button", { name: "Edit image", exact: true }).click();
    const canvas = page.getByRole("dialog").locator("canvas");
    await expect(canvas).toHaveAttribute("width", "600");
    await expect(canvas).toHaveAttribute("height", "350");
    return canvas;
}

test("Edit image loads current bytes and uses their revision when saving", async ({
    page,
}) => {
    await initial(page);
    await page.route("**/test-latest-evidence", (route) =>
        route.fulfill({ json: metadata() })
    );
    let downloadRevision = "";
    await page.route(
        "**/reporting/evidence/download/1?expected_document=*",
        async (route) => {
            downloadRevision = new URL(route.request().url()).searchParams.get(
                "expected_document"
            )!;
            await route.fulfill({
                contentType: "image/png",
                body: await image(page),
            });
        }
    );
    const canvas = await open(page);
    expect(downloadRevision).toBe("current.png");
    expect(
        await canvas.evaluate((canvas: HTMLCanvasElement) => [
            ...canvas.getContext("2d")!.getImageData(100, 100, 1, 1).data,
        ])
    ).toEqual([109, 112, 167, 255]);
    await page.getByRole("button", { name: "Line", exact: true }).click();
    const box = (await canvas.boundingBox())!;
    await page.mouse.move(box.x + 30, box.y + 30);
    await page.mouse.down();
    await page.mouse.move(box.x + 70, box.y + 30);
    await page.mouse.up();
    let body = "";
    await page.route("**/test-replace-image/1", async (route) => {
        body = route.request().postDataBuffer()!.toString();
        await route.fulfill({ json: {} });
    });
    await page
        .getByRole("button", { name: "Replace evidence image", exact: true })
        .click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expect(body).toContain('name="expected_document"\r\n\r\ncurrent.png');
});

test("every open refreshes the revision instead of reusing the prior editor source", async ({
    page,
}) => {
    await initial(page);
    let reads = 0;
    await page.route("**/test-latest-evidence", (route) =>
        route.fulfill({
            json: metadata(++reads === 1 ? "current.png" : "newer.png"),
        })
    );
    await page.route(
        "**/reporting/evidence/download/1?expected_document=*",
        async (route) => {
            const revision = new URL(route.request().url()).searchParams.get(
                "expected_document"
            );
            await route.fulfill({
                contentType: "image/png",
                body: await image(
                    page,
                    revision === "current.png" ? 600 : 640,
                    revision === "current.png" ? 350 : 400
                ),
            });
        }
    );
    await open(page);
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await page.getByRole("button", { name: "Edit image", exact: true }).click();
    await expect(page.getByRole("dialog").locator("canvas")).toHaveAttribute(
        "width",
        "640"
    );
    await expect(page.getByRole("dialog").locator("canvas")).toHaveAttribute(
        "height",
        "400"
    );
    expect(reads).toBe(2);
});

test("a replacement during download refetches metadata before opening", async ({
    page,
}) => {
    await initial(page);
    let reads = 0;
    const revisions: string[] = [];
    await page.route("**/test-latest-evidence", (route) =>
        route.fulfill({
            json: metadata(++reads === 1 ? "racing.png" : "current.png"),
        })
    );
    await page.route(
        "**/reporting/evidence/download/1?expected_document=*",
        async (route) => {
            const revision = new URL(route.request().url()).searchParams.get(
                "expected_document"
            )!;
            revisions.push(revision);
            if (revision === "racing.png")
                await route.fulfill({
                    status: 409,
                    json: { document: ["Changed"] },
                });
            else
                await route.fulfill({
                    contentType: "image/png",
                    body: await image(page),
                });
        }
    );
    await open(page);
    expect(reads).toBe(2);
    expect(revisions).toEqual(["racing.png", "current.png"]);
});

for (const failure of [
    "metadata",
    "login",
    "download",
    "repeated-conflict",
    "removed",
    "not-image",
] as const) {
    test(`opening failure (${failure}) never falls back to the cached image`, async ({
        page,
    }) => {
        await initial(page);
        await page.route("**/test-latest-evidence", (route) =>
            failure === "metadata"
                ? route.fulfill({ status: 503 })
                : route.fulfill({
                      json:
                          failure === "removed"
                              ? []
                              : metadata(
                                    failure === "not-image"
                                        ? "notes.txt"
                                        : "current.png"
                                ),
                  })
        );
        let downloads = 0;
        await page.route(
            "**/reporting/evidence/download/1?expected_document=*",
            async (route) => {
                downloads++;
                if (failure === "repeated-conflict")
                    await route.fulfill({ status: 409, json: {} });
                else if (failure === "login")
                    await route.fulfill({
                        contentType: "text/html",
                        body: "Sign in",
                    });
                else await route.fulfill({ status: 503 });
            }
        );
        await page
            .getByRole("button", { name: "Edit image", exact: true })
            .click();
        await expect(page.getByRole("alert")).toBeVisible();
        await expect(page.getByRole("dialog")).toHaveCount(0);
        const edit = page.getByRole("button", {
            name: "Edit image",
            exact: true,
        });
        if (failure === "removed" || failure === "not-image")
            await expect(edit).toHaveCount(0);
        else await expect(edit).toBeEnabled();
        expect(downloads).toBe(
            failure === "repeated-conflict"
                ? 2
                : ["metadata", "removed", "not-image"].includes(failure)
                  ? 0
                  : 1
        );
    });
}

test("opening locks repeat clicks and reports loading until the current download arrives", async ({
    page,
}) => {
    await initial(page);
    let release!: () => void;
    const pending = new Promise<void>((resolve) => {
        release = resolve;
    });
    let reads = 0;
    await page.route("**/test-latest-evidence", async (route) => {
        reads++;
        await pending;
        await route.fulfill({ json: metadata() });
    });
    await page.route(
        "**/reporting/evidence/download/1?expected_document=*",
        async (route) =>
            route.fulfill({ contentType: "image/png", body: await image(page) })
    );
    await page.getByRole("button", { name: "Edit image", exact: true }).click();
    const button = page.getByRole("button", {
        name: "Loading image…",
        exact: true,
    });
    await expect(button).toBeDisabled();
    await button.evaluate((button: HTMLButtonElement) => {
        button.click();
        button.click();
    });
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expect(reads).toBe(1);
    release();
    await expect(page.getByRole("dialog").locator("canvas")).toHaveAttribute(
        "width",
        "600"
    );
});

test("a completed open cannot resurrect an evidence view removed during loading", async ({
    page,
}) => {
    await initial(page);
    let release!: () => void;
    const pending = new Promise<void>((resolve) => {
        release = resolve;
    });
    await page.route("**/test-latest-evidence", async (route) => {
        await pending;
        await route.fulfill({ json: metadata() });
    });
    await page.route(
        "**/reporting/evidence/download/1?expected_document=*",
        async (route) =>
            route.fulfill({ contentType: "image/png", body: await image(page) })
    );
    await page.getByRole("button", { name: "Edit image", exact: true }).click();
    await page
        .getByRole("button", { name: "Remove evidence view", exact: true })
        .click();
    release();
    await expect(page.locator(".richtext-evidence")).toHaveCount(0);
    await expect(page.getByRole("dialog")).toHaveCount(0);
});
