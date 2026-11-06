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
const template = readFileSync(
    path.join(
        repositoryRoot,
        "ghostwriter/oplog/templates/oplog/oplog_detail.html"
    ),
    "utf8"
);
const document = new Window().document;
document.body.innerHTML = template;
const buttonMarkup = document.querySelector("#columnSelectDropdown")!.outerHTML;
const columnsMarkup = document.querySelector("#columnSelect")!.outerHTML;
const script = readFileSync(path.join(staticRoot, "js/oplog.js"), "utf8");
// Exercise the production handler without initializing unrelated log data or sockets.
const columnsHandler = script.match(
    /    \$\('#columnSelectDropdown'\)\.click\(function \(\) \{[\s\S]*?^    \}\);/m
)?.[0];
if (!columnsHandler) throw new Error("Missing Columns click handler");

async function renderColumns(page: Page, theme: string) {
    await page.setContent(`<html data-theme="${theme}" data-bs-theme="${theme}">
        <body><h1>Activity log</h1>
            <div class="oplog-toolbar"><div class="oplog-toolbar-actions">${buttonMarkup}</div></div>
            ${columnsMarkup}
        </body></html>`);
    for (const stylesheet of [
        "vendor/bootstrap/5.3.8/css/bootstrap.min.css",
        "css/bootstrap5_compat.css",
        "css/base_styles.css",
        "css/styles.css",
        "css/app_shell.css",
        "css/design_system.css",
    ]) {
        await page.addStyleTag({ path: path.join(staticRoot, stylesheet) });
    }
    await page.addScriptTag({
        path: path.join(staticRoot, "js/jquery-3.6.1.min.js"),
    });
    await page.addScriptTag({ content: columnsHandler });
}

for (const theme of ["light", "dark"]) {
    for (const reducedMotion of ["reduce", "no-preference"] as const) {
        test(`Columns rotates only its glyph after mouse-out in ${theme} with ${reducedMotion} motion`, async ({
            page,
        }) => {
            await page.emulateMedia({ reducedMotion });
            await renderColumns(page, theme);
            const button = page.getByRole("button", { name: "Columns" });
            const icon = button.locator(".oplog-columns-icon");
            const columns = page.locator("#columnSelect");

            await expect(columns).toBeHidden();
            await expect(button).toHaveCSS("transform", "none");
            await expect(icon).toHaveCSS("transform", "none");

            await button.click();
            await expect(button).toHaveAttribute("aria-expanded", "true");
            await expect(columns).toBeVisible();
            await expect(button).toHaveCSS("transform", "none");
            await page.getByRole("heading").hover();
            await expect(button).toHaveCSS("transform", "none");
            await expect(icon).toHaveCSS(
                "transform",
                "matrix(0, 1, -1, 0, 0, 0)"
            );
            if (reducedMotion === "reduce") {
                await expect(icon).toHaveCSS("transition-duration", "0s");
            }

            // Native keyboard activation must keep disclosure state and visibility aligned.
            for (const key of ["Enter", "Space"]) {
                await button.press(key);
                await expect(button).toHaveAttribute("aria-expanded", "false");
                await expect(columns).toBeHidden();
                await expect(button).toHaveCSS("transform", "none");
                await expect(icon).toHaveCSS("transform", "none");
                await button.press(key);
                await expect(button).toHaveAttribute("aria-expanded", "true");
                await expect(columns).toBeVisible();
                await expect(button).toHaveCSS("transform", "none");
                await expect(icon).toHaveCSS(
                    "transform",
                    "matrix(0, 1, -1, 0, 0, 0)"
                );
            }
        });
    }
}
