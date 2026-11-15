import { expect, Page, test } from "@playwright/test";

async function selectFile(page: Page, name = "proof.png") {
    const source = await page.evaluate(() => window.imageEditorTest.fixture());
    await page.locator('input[type="file"]').setInputFiles({
        name,
        mimeType: "image/png",
        buffer: Buffer.from(source.split(",")[1], "base64"),
    });
}

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

async function pasteReplacement(page: Page) {
    await page.evaluate(async () => {
        const canvas = document.createElement("canvas");
        canvas.width = 17;
        canvas.height = 13;
        canvas.getContext("2d")!.fillRect(0, 0, 17, 13);
        const blob = await new Promise<Blob>((resolve) =>
            canvas.toBlob((value) => resolve(value!), "image/png")
        );
        const clipboard = new DataTransfer();
        clipboard.items.add(
            new File([blob], "pasted-replacement.png", { type: "image/png" })
        );
        document.querySelector("canvas")!.dispatchEvent(
            new ClipboardEvent("paste", {
                clipboardData: clipboard,
                bubbles: true,
                cancelable: true,
            })
        );
    });
}

async function drawArea(page: Page) {
    const canvas = page.locator("canvas");
    const box = (await canvas.boundingBox())!;
    await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.6);
    await page.mouse.up();
}

for (const activation of ["Enter", "Space", "click"] as const) {
    test(`report-size Cancel uses native ${activation} activation without saving`, async ({
        page,
    }) => {
        await page.goto("/?evidence");
        await page.evaluate(() => window.imageEditorTest.connected());
        await page.getByRole("button", { name: /Report size:/ }).click();
        await page
            .getByLabel("Report size unit", { exact: true })
            .selectOption("percent");
        await page.getByLabel("Percent of width", { exact: true }).fill("35");
        const cancel = page.getByRole("button", {
            name: "Cancel",
            exact: true,
        });
        if (activation === "click") await cancel.click();
        else {
            await cancel.focus();
            await page.keyboard.press(activation);
        }
        await expect(
            page.getByLabel("Percent of width", { exact: true })
        ).toHaveCount(0);
        expect(
            await page.evaluate(() => window.imageEditorTest.savedSizes)
        ).toEqual([]);
    });
}

test("report-size inputs and Apply still support Enter to save", async ({
    page,
}) => {
    await page.goto("/?evidence");
    await page.evaluate(() => window.imageEditorTest.connected());
    for (const value of [35, 42]) {
        await page.getByRole("button", { name: /Report size:/ }).click();
        await page
            .getByLabel("Report size unit", { exact: true })
            .selectOption("percent");
        const input = page.getByLabel("Percent of width", { exact: true });
        await input.fill(String(value));
        if (value === 35) await input.press("Enter");
        else {
            await page
                .getByRole("button", { name: "Apply", exact: true })
                .focus();
            await page.keyboard.press("Enter");
        }
        await expect(input).toHaveCount(0);
    }
    expect(
        await page.evaluate(() => window.imageEditorTest.savedSizes)
    ).toEqual([
        { id: 1, unit: "percent", value: 35 },
        { id: 1, unit: "percent", value: 42 },
    ]);
});

test("standalone editor blocks paste, file changes, and form submission until cancellation", async ({
    page,
}) => {
    await page.goto("/?evidence-page");
    await selectFile(page, "original.png");
    const before = await fileSnapshot(page);
    await page
        .getByRole("button", { name: "Edit evidence image", exact: true })
        .click();
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await expect(page.locator('input[type="file"]')).toBeDisabled();
    await expect(
        page.getByRole("button", {
            name: "Save Changes",
            exact: true,
            includeHidden: true,
        })
    ).toBeDisabled();
    await pasteReplacement(page);
    expect(await fileSnapshot(page)).toEqual(before);
    await page.evaluate(() => {
        const input =
            document.querySelector<HTMLInputElement>('input[type="file"]')!;
        const replacement = new DataTransfer();
        replacement.items.add(
            new File(["replacement"], "replacement.txt", { type: "text/plain" })
        );
        input.files = replacement.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
        input.form!.requestSubmit();
    });
    expect(await fileSnapshot(page)).toEqual(before);
    expect(
        await page.evaluate(() => window.imageEditorTest.formSubmissions)
    ).toBe(0);
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(page.locator('input[type="file"]')).toBeEnabled();
    await expect(
        page.getByRole("button", { name: "Save Changes", exact: true })
    ).toBeEnabled();
    expect(await fileSnapshot(page)).toEqual(before);
    await expect(page.locator('input[name="document_was_edited"]')).toHaveValue(
        "false"
    );
    await page
        .getByRole("button", { name: "Save Changes", exact: true })
        .click();
    expect(
        await page.evaluate(() => window.imageEditorTest.formSubmissions)
    ).toBe(1);
});

test("standalone staged PNG and edited-file flag survive reopening and cancel", async ({
    page,
}) => {
    await page.goto("/?evidence-page");
    await page
        .getByRole("button", { name: "Edit evidence image", exact: true })
        .click();
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await drawArea(page);
    await page
        .getByRole("button", { name: "Use edited image", exact: true })
        .click();
    await expect(page.locator('input[name="document_was_edited"]')).toHaveValue(
        "true"
    );
    const edited = await fileSnapshot(page);
    expect(edited).not.toBeNull();
    await page
        .getByRole("button", { name: "Edit evidence image", exact: true })
        .click();
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await pasteReplacement(page);
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    expect(await fileSnapshot(page)).toEqual(edited);
    await expect(page.locator('input[name="document_was_edited"]')).toHaveValue(
        "true"
    );
    await page.locator('input[type="file"]').setInputFiles([]);
    await expect(page.locator('input[name="document_was_edited"]')).toHaveValue(
        "true"
    );
    await selectFile(page, "explicit-replacement.png");
    await expect(page.locator('input[name="document_was_edited"]')).toHaveValue(
        "false"
    );
});

test("successful edited-image upload completes even when evidence refresh fails", async ({
    page,
}) => {
    let writes = 0;
    await page.route("**/test-upload", async (route) => {
        writes++;
        await route.fulfill({ json: { pk: 42 } });
    });
    await page.goto("/?upload");
    await page.evaluate(() => {
        window.imageEditorTest.uploadPollFailure = true;
    });
    await page
        .getByLabel("Friendly name", { exact: true })
        .fill("Edited evidence");
    await page.getByLabel("Caption", { exact: true }).fill("An edited image");
    await selectFile(page);
    await page
        .getByRole("button", {
            name: "Edit image before uploading",
            exact: true,
        })
        .click();
    await expect(page.locator("canvas")).toHaveAttribute("width", "400");
    await drawArea(page);
    await page
        .getByRole("button", { name: "Use edited image", exact: true })
        .click();
    await page
        .getByRole("button", { name: "Upload and insert", exact: true })
        .click();
    await expect
        .poll(() => page.evaluate(() => window.imageEditorTest.uploaded))
        .toBe(42);
    await expect(
        page.getByText("Could not create evidence", { exact: true })
    ).toHaveCount(0);
    await expect(
        page.getByRole("button", { name: "Uploading…", exact: true })
    ).toBeDisabled();
    await page
        .locator("form")
        .evaluate((form: HTMLFormElement) => form.requestSubmit());
    expect(writes).toBe(1);
});

test("pending upload locks modal cancellation until the successful result arrives", async ({
    page,
}) => {
    let release!: () => void;
    const pending = new Promise<void>((resolve) => {
        release = resolve;
    });
    let writes = 0;
    await page.route("**/test-upload", async (route) => {
        writes++;
        await pending;
        await route.fulfill({ json: { pk: 43 } });
    });
    await page.goto("/?upload-dialog");
    await page.getByLabel("Caption", { exact: true }).fill("Pending upload");
    await page
        .getByRole("button", { name: "Upload and insert", exact: true })
        .click();
    await expect(
        page.getByRole("button", { name: "Uploading…", exact: true })
    ).toBeDisabled();
    await expect(
        page.getByRole("button", { name: "Cancel", exact: true })
    ).toBeDisabled();
    await expect(
        page.getByRole("button", { name: "Choose existing", exact: true })
    ).toBeDisabled();
    await expect(
        page.getByRole("button", { name: "Close", exact: true })
    ).toBeDisabled();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect.poll(() => writes).toBe(1);
    release();
    await expect
        .poll(() => page.evaluate(() => window.imageEditorTest.uploaded))
        .toBe(43);
    await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("failed upload preserves the file and unlocks modal cancellation", async ({
    page,
}) => {
    await page.route("**/test-upload", (route) =>
        route.fulfill({ status: 503 })
    );
    await page.goto("/?upload-dialog");
    await page.getByLabel("Caption", { exact: true }).fill("Retryable upload");
    const selected = await fileSnapshot(page);
    await page
        .getByRole("button", { name: "Upload and insert", exact: true })
        .click();
    await expect(page.getByRole("alert")).toContainText(
        "Could not create evidence"
    );
    expect(await fileSnapshot(page)).toEqual(selected);
    await expect(
        page.getByRole("button", { name: "Upload and insert", exact: true })
    ).toBeEnabled();
    await expect(
        page.getByRole("button", { name: "Close", exact: true })
    ).toBeEnabled();
    await expect(
        page.getByRole("button", { name: "Choose existing", exact: true })
    ).toBeEnabled();
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
});
