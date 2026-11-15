import { expect, Page, test } from "@playwright/test";

async function fileSnapshot(page: Page) {
    return page
        .locator('input[type="file"]')
        .evaluate(async (input: HTMLInputElement) => {
            const file = input.files?.[0];
            return file
                ? {
                      name: file.name,
                      bytes: [...new Uint8Array(await file.arrayBuffer())],
                  }
                : null;
        });
}
async function stage(page: Page) {
    await page
        .getByRole("button", { name: "Edit evidence image", exact: true })
        .click();
    const canvas = page.locator("canvas");
    await expect(canvas).toHaveAttribute("width", "400");
    const box = (await canvas.boundingBox())!;
    await page.mouse.move(box.x + 20, box.y + 20);
    await page.mouse.down();
    await page.mouse.move(box.x + 100, box.y + 100);
    await page.mouse.up();
    await page
        .getByRole("button", { name: "Use edited image", exact: true })
        .click();
    await expect(page.locator('[name="document_was_edited"]')).toHaveValue(
        "true"
    );
}

test.beforeEach(async ({ page }) => {
    await page.route("**/test-evidence-metadata", (route) =>
        route.fulfill({
            json: {
                document: "latest.png",
                download_url: "/test-current-image",
            },
        })
    );
    await page.route("**/test-current-image?*", async (route) => {
        expect(
            new URL(route.request().url()).searchParams.get("expected_document")
        ).toBe("latest.png");
        const source = await page.evaluate(() =>
            window.imageEditorTest.fixture()
        );
        await route.fulfill({
            contentType: "image/png",
            body: Buffer.from(source.split(",")[1], "base64"),
        });
    });
    await page.route("**/test-saved", (route) =>
        route.fulfill({ contentType: "text/html", body: "<p>Saved</p>" })
    );
    await page.goto("/?async-form");
});

test("server validation retains exact edited file and all values for successful retry", async ({
    page,
}) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    let writes = 0;
    let savedBody: Buffer | null = null;
    await page.route("**/test-evidence-save", async (route) => {
        writes++;
        savedBody = route.request().postDataBuffer();
        await route.fulfill(
            writes === 1
                ? {
                      status: 400,
                      json: {
                          errors: {
                              friendly_name: [
                                  "This friendly name has already been used.",
                              ],
                          },
                      },
                  }
                : { json: { redirect_url: "/test-saved" } }
        );
    });
    await stage(page);
    const before = await fileSnapshot(page);
    expect(before).not.toBeNull();
    await page
        .getByRole("textbox", { name: "Description", exact: true })
        .fill("Preserve this description");
    await page
        .getByRole("button", { name: "Save Changes", exact: true })
        .click();
    await expect(page.getByRole("alert")).toContainText("already been used");
    expect(await fileSnapshot(page)).toEqual(before);
    await expect(
        page.getByRole("textbox", { name: "Description", exact: true })
    ).toHaveValue("Preserve this description");
    await expect(page.locator('[name="expected_document"]')).toHaveValue(
        "latest.png"
    );
    await expect(page.locator('[name="document_was_edited"]')).toHaveValue(
        "true"
    );
    await expect(
        page.getByLabel("Friendly name", { exact: true })
    ).toHaveAttribute("aria-invalid", "true");
    await expect(
        page.getByLabel("Originally disabled", { exact: true })
    ).toBeDisabled();
    await page
        .getByLabel("Friendly name", { exact: true })
        .fill("Corrected name");
    await page
        .getByRole("button", { name: "Save Changes", exact: true })
        .click();
    await page.waitForURL("**/test-saved");
    expect(writes).toBe(2);
    expect(savedBody!.includes(Buffer.from(before!.bytes))).toBe(true);
    expect(savedBody!.toString()).toContain("Corrected name");
    expect(errors).toEqual([]);
});

test("native required validation retains staged file without a request", async ({
    page,
}) => {
    let writes = 0;
    await page.route("**/test-evidence-save", (route) => {
        writes++;
        return route.abort();
    });
    await stage(page);
    const before = await fileSnapshot(page);
    await page.getByLabel("Caption", { exact: true }).fill("");
    await page
        .getByRole("button", { name: "Save Changes", exact: true })
        .click();
    expect(
        await page
            .getByLabel("Caption", { exact: true })
            .evaluate((e: HTMLInputElement) => e.validity.valueMissing)
    ).toBe(true);
    expect(writes).toBe(0);
    expect(await fileSnapshot(page)).toEqual(before);
});

for (const failure of [
    "conflict",
    "storage",
    "network",
    "login",
    "unsafe-redirect",
] as const) {
    test(`${failure} response preserves edits and restores controls`, async ({
        page,
    }) => {
        await page.route("**/test-evidence-save", async (route) => {
            if (failure === "network") return route.abort("failed");
            if (failure === "login")
                return route.fulfill({
                    contentType: "text/html",
                    body: "<form>Sign in</form>",
                });
            if (failure === "unsafe-redirect")
                return route.fulfill({
                    json: { redirect_url: "https://example.invalid/" },
                });
            return route.fulfill({
                status: failure === "conflict" ? 409 : 503,
                json: {
                    errors: {
                        document: [
                            failure === "conflict"
                                ? "Image changed. Reload the page."
                                : "Storage unavailable. Try again.",
                        ],
                    },
                },
            });
        });
        await stage(page);
        const before = await fileSnapshot(page);
        await page
            .getByRole("button", { name: "Save Changes", exact: true })
            .click();
        await expect(page.getByRole("alert")).toBeVisible();
        expect(await fileSnapshot(page)).toEqual(before);
        await expect(
            page.getByRole("button", { name: "Save Changes", exact: true })
        ).toBeEnabled();
        await expect(page.locator('input[type="file"]')).toBeEnabled();
        await expect(
            page.getByLabel("Originally disabled", { exact: true })
        ).toBeDisabled();
        await expect(page.locator('[name="document_was_edited"]')).toHaveValue(
            "true"
        );
        expect(new URL(page.url()).search).toBe("?async-form");
    });
}

test("pending request locks file changes, cancellation and duplicate submissions", async ({
    page,
}) => {
    let writes = 0;
    let release!: () => void;
    const pending = new Promise<void>((resolve) => {
        release = resolve;
    });
    await page.route("**/test-evidence-save", async (route) => {
        writes++;
        await pending;
        await route.fulfill({
            status: 400,
            json: { errors: { __all__: ["Retry"] } },
        });
    });
    await stage(page);
    const before = await fileSnapshot(page);
    await page
        .getByRole("button", { name: "Save Changes", exact: true })
        .click();
    await expect(page.locator("form")).toHaveAttribute("aria-busy", "true");
    await expect(page.locator('input[type="file"]')).toBeDisabled();
    await page.locator("form").evaluate((form: HTMLFormElement) => {
        form.requestSubmit();
        form.requestSubmit();
    });
    await page.getByRole("link", { name: "Cancel", exact: true }).click();
    expect(new URL(page.url()).search).toBe("?async-form");
    expect(writes).toBe(1);
    release();
    await expect(page.getByRole("alert")).toContainText("Retry");
    expect(await fileSnapshot(page)).toEqual(before);
});

test("open image editor prevents form submission before async handler", async ({
    page,
}) => {
    let writes = 0;
    await page.route("**/test-evidence-save", (route) => {
        writes++;
        return route.abort();
    });
    await page
        .getByRole("button", { name: "Edit evidence image", exact: true })
        .click();
    await expect(page.locator("canvas")).toBeVisible();
    await page
        .locator("form")
        .evaluate((form: HTMLFormElement) => form.requestSubmit());
    expect(writes).toBe(0);
    await expect(page.locator("canvas")).toBeVisible();
});

test("server errors are displayed as text without executing markup", async ({
    page,
}) => {
    await page.route("**/test-evidence-save", (route) =>
        route.fulfill({
            status: 400,
            json: {
                errors: {
                    friendly_name: [
                        '<img src=x onerror="window.injected=true">',
                    ],
                },
            },
        })
    );
    await stage(page);
    await page
        .getByRole("button", { name: "Save Changes", exact: true })
        .click();
    await expect(page.getByRole("alert")).toContainText("<img src=x");
    await expect(page.getByRole("alert").locator("img")).toHaveCount(0);
});

test("every server-image open refreshes revision but reopening staged edits retains them", async ({
    page,
}) => {
    let fetches = 0;
    await page.route("**/test-evidence-metadata", async (route) => {
        fetches++;
        await route.fulfill({
            json: {
                document: "latest.png",
                download_url: "/test-current-image",
            },
        });
    });
    for (let i = 0; i < 2; i++) {
        await page
            .getByRole("button", { name: "Edit evidence image", exact: true })
            .click();
        await expect(page.locator("canvas")).toBeVisible();
        await page.getByRole("button", { name: "Cancel", exact: true }).click();
    }
    expect(fetches).toBe(2);
    await stage(page);
    expect(fetches).toBe(3);
    const before = await fileSnapshot(page);
    await page
        .getByRole("button", { name: "Edit evidence image", exact: true })
        .click();
    await expect(page.locator("canvas")).toBeVisible();
    expect(fetches).toBe(3);
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    expect(await fileSnapshot(page)).toEqual(before);
});

test("fresh-source failure opens no cached image and restores form controls", async ({
    page,
}) => {
    await page.route("**/test-evidence-metadata", (route) =>
        route.fulfill({ status: 503, json: {} })
    );
    await page
        .getByRole("button", { name: "Edit evidence image", exact: true })
        .click();
    await expect(page.getByRole("alert")).toContainText(
        "latest image could not be loaded"
    );
    await expect(page.locator("canvas")).toHaveCount(0);
    await expect(page.locator('input[type="file"]')).toBeEnabled();
    await expect(
        page.getByRole("button", { name: "Save Changes", exact: true })
    ).toBeEnabled();
    await expect(page.locator('[name="expected_document"]')).toHaveValue(
        "old.png"
    );
});

test("evidence without an existing file can stage and retain a new image", async ({
    page,
}) => {
    await page.goto("/?async-form&blank");
    await expect(
        page.getByRole("button", { name: "Edit evidence image", exact: true })
    ).toHaveCount(0);
    const source = await page.evaluate(() => window.imageEditorTest.fixture());
    await page.locator('input[type="file"]').setInputFiles({
        name: "new-proof.png",
        mimeType: "image/png",
        buffer: Buffer.from(source.split(",")[1], "base64"),
    });
    await page.route("**/test-evidence-save", (route) =>
        route.fulfill({
            status: 400,
            json: { errors: { friendly_name: ["Choose another name."] } },
        })
    );
    await stage(page);
    const staged = await fileSnapshot(page);
    await page
        .getByRole("button", { name: "Save Changes", exact: true })
        .click();
    await expect(page.getByRole("alert")).toContainText("Choose another name");
    expect(await fileSnapshot(page)).toEqual(staged);
});

test("rotated CSRF cookie updates both multipart token and header", async ({
    page,
    context,
}) => {
    await stage(page);
    const cookieToken = "rotated-current-csrf-token";
    await context.addCookies([
        { name: "csrftoken", value: cookieToken, url: "http://127.0.0.1:4178" },
    ]);
    await page.route("**/test-evidence-save", async (route) => {
        const request = route.request();
        expect(request.headers()["x-csrftoken"]).toBe(cookieToken);
        const body = request.postDataBuffer()!.toString();
        expect(body).toContain(
            `name="csrfmiddlewaretoken"\r\n\r\n${cookieToken}`
        );
        expect(body).not.toContain("fixture-csrf-token");
        await route.fulfill({
            status: 400,
            json: { errors: { friendly_name: ["Correct this name."] } },
        });
    });
    const staged = await fileSnapshot(page);
    await page
        .getByRole("button", { name: "Save Changes", exact: true })
        .click();
    await expect(page.getByRole("alert")).toContainText("Correct this name");
    expect(await fileSnapshot(page)).toEqual(staged);
});
