import { expect, test, type Page } from "@playwright/test";
import { Window } from "happy-dom";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../../.."
);
const staticRoot = path.join(repositoryRoot, "ghostwriter/static");

function templateScript(filename: string, marker: string) {
    const template = readFileSync(path.join(repositoryRoot, filename), "utf8");
    const window = new Window();
    const document = new window.DOMParser().parseFromString(
        template,
        "text/html"
    );
    const script = Array.from(document.querySelectorAll("script")).find(
        (script) => script.textContent.includes(marker)
    );
    if (!script) throw new Error(`Missing production handler: ${marker}`);
    return script.textContent;
}

const addHandler = templateScript(
    "ghostwriter/shepherd/templates/shepherd/server_form.html",
    ".formset-add-{{ addresses.prefix }}"
);
const deleteHandlers = templateScript(
    "ghostwriter/templates/base_generic.html",
    "$(document).on('click', '.formset-del-button'"
);

function entry(prefix: string, index: string) {
    return `<div class="formset-container">
        <div class="formset">
            <span class="counter">1</span>
            <input type="hidden" name="${prefix}-${index}-id">
            <input aria-label="Disabled field" disabled>
            <input aria-label="Hidden field" style="display: none">
            <label>Address <input id="id_${prefix}-${index}-address" name="${prefix}-${index}-address"></label>
            <input type="checkbox" id="id_${prefix}-${index}-DELETE" name="${prefix}-${index}-DELETE" hidden>
            <div class="formset-actions"><button type="button" class="formset-del-button">Delete</button></div>
        </div>
        <div class="alert" style="display: none">
            Deleted <button type="button" class="formset-undo-button">Undo</button>
        </div>
    </div>`;
}

async function renderCollections(page: Page) {
    await page.setContent(
        `<form>${["addresses", "alternate"]
            .map(
                (prefix) => `
        <div class="tab-pane">
            <input type="hidden" id="id_${prefix}-TOTAL_FORMS" value="1">
            <input type="button" id="add-${prefix}" class="formset-add-${prefix}" value="Add address">
            <div id="formset-${prefix}" data-formset-prefix="${prefix}">${entry(prefix, "0")}</div>
            <div id="empty-form-${prefix}" style="display: none">${entry(prefix, "__prefix__")}</div>
        </div>`
            )
            .join("")}</form>`
    );
    await page.addScriptTag({
        path: path.join(staticRoot, "js/jquery-3.6.1.min.js"),
    });
    await page.addScriptTag({ content: deleteHandlers });
    // The editor runtime is independent of the Add action under test.
    await page.addScriptTag({
        content: `
        window.gwInitTiptapTextareas = function (entry) {
            entry.dataset.editorInitialized = 'true';
        };
        document.querySelectorAll('[id^="add-"]').forEach(function (source) {
            source.addEventListener('click', function () {
                source.dataset.clicks = String(Number(source.dataset.clicks || 0) + 1);
            });
        });
    `,
    });
    for (const prefix of ["addresses", "alternate"]) {
        await page.addScriptTag({
            content: addHandler.replaceAll("{{ addresses.prefix }}", prefix),
        });
    }
    await page.addScriptTag({
        path: path.join(staticRoot, "js/collection-add-footer.js"),
    });
}

test.beforeEach(async ({ page }) => {
    await renderCollections(page);
});

test("duplicated Add forwards once, creates an entry, and focuses its first usable field", async ({
    page,
}) => {
    const entries = page.locator("#formset-addresses > .formset-container");
    await entries.first().getByRole("button", { name: "Add address" }).click();

    await expect(entries).toHaveCount(2);
    await expect(page.locator("#add-addresses")).toHaveAttribute(
        "data-clicks",
        "1"
    );
    await expect(page.locator("#id_addresses-TOTAL_FORMS")).toHaveValue("2");
    await expect(page.locator("#id_addresses-1-address")).toBeFocused();
    await expect(entries.last()).toHaveAttribute(
        "data-editor-initialized",
        "true"
    );
    await expect(entries.last().locator(".counter")).toHaveText("2");
    await expect(page.locator(".formset-add-addresses")).toHaveCount(1);
    await expect(entries.locator(".collection-add-button")).toHaveCount(2);
    await expect(
        page.locator("#formset-alternate > .formset-container")
    ).toHaveCount(1);
    await expect(page.locator("#id_alternate-TOTAL_FORMS")).toHaveValue("1");

    // A newly inserted action must work too, including native keyboard activation.
    await entries
        .last()
        .getByRole("button", { name: "Add address" })
        .press("Enter");
    await expect(entries).toHaveCount(3);
    await expect(page.locator("#add-addresses")).toHaveAttribute(
        "data-clicks",
        "2"
    );
    await expect(page.locator("#id_addresses-TOTAL_FORMS")).toHaveValue("3");
    await expect(page.locator("#id_addresses-2-address")).toBeFocused();
});

test("Delete and Undo update the duplicated action after the document handlers", async ({
    page,
}) => {
    const entry = page
        .locator("#formset-addresses > .formset-container")
        .first();
    const action = entry.locator(".collection-add-button");
    const deleted = entry.locator('input[name$="-DELETE"]');

    await entry.getByRole("button", { name: "Delete", exact: true }).click();
    await expect(deleted).toBeChecked();
    // Check its own hidden flag: hiding the parent alone would conceal a regression.
    await expect(action).toHaveJSProperty("hidden", true);
    await entry.getByRole("button", { name: "Undo", exact: true }).click();
    await expect(deleted).not.toBeChecked();
    await expect(action).toHaveJSProperty("hidden", false);
    await expect(action).toBeVisible();
    await action.click();
    await expect(page.locator("#id_addresses-TOTAL_FORMS")).toHaveValue("2");
});

test("DELETE changes update only the matching collection's action", async ({
    page,
}) => {
    const entry = page
        .locator("#formset-alternate > .formset-container")
        .first();
    const action = entry.locator(".collection-add-button");
    const deleted = entry.locator('input[name$="-DELETE"]');
    await deleted.evaluate((input: HTMLInputElement) => {
        input.checked = true;
        input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await expect(action).toHaveJSProperty("hidden", true);
    await expect(
        page.locator("#formset-addresses .collection-add-button")
    ).toBeVisible();
    await deleted.evaluate((input: HTMLInputElement) => {
        input.checked = false;
        input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await expect(action).toHaveJSProperty("hidden", false);
    await action.click();
    await expect(page.locator("#id_alternate-1-address")).toBeFocused();
    await expect(page.locator("#id_alternate-TOTAL_FORMS")).toHaveValue("2");
    await expect(page.locator("#id_addresses-TOTAL_FORMS")).toHaveValue("1");
});
