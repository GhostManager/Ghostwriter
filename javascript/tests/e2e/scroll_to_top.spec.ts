import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../../.."
);
const staticRoot = path.join(repositoryRoot, "ghostwriter/static");
const snippet = readFileSync(
    path.join(
        repositoryRoot,
        "ghostwriter/templates/snippets/scroll_to_top.html"
    ),
    "utf8"
);
const buttonMarkup = snippet
    .split("<script")[0]
    .replace("{% load static %}", "");

async function renderScrollControl(page: Page) {
    await page.setContent(`<html><body>
        <main style="height: 2400px">Long page</main>${buttonMarkup}
    </body></html>`);
    await page.addStyleTag({
        path: path.join(staticRoot, "css/design_system.css"),
    });
    await page.addScriptTag({
        path: path.join(staticRoot, "js/scroll-to-top.js"),
    });
}

test("scroll control is hidden through 300px and visible above the threshold", async ({
    page,
}) => {
    await renderScrollControl(page);
    const button = page.getByRole("button", {
        name: "Scroll to top",
        includeHidden: true,
    });
    await expect(button).toBeHidden();
    for (const top of [300, 301, 300, 0]) {
        await page.evaluate(
            (top) => window.scrollTo({ top, behavior: "instant" }),
            top
        );
        await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(top);
        await expect(button).toHaveJSProperty("hidden", top <= 300);
        if (top > 300) await expect(button).toBeVisible();
        else await expect(button).toBeHidden();
    }
});

for (const reducedMotion of ["reduce", "no-preference"] as const) {
    for (const key of ["Enter", "Space"]) {
        test(`keyboard ${key} returns to the top with ${reducedMotion} motion`, async ({
            page,
        }) => {
            await page.emulateMedia({ reducedMotion });
            await renderScrollControl(page);
            await page.evaluate(() =>
                window.scrollTo({ top: 500, behavior: "instant" })
            );
            const button = page.getByRole("button", { name: "Scroll to top" });
            await expect(button).toBeVisible();

            // Observe the requested behavior while retaining native scrolling.
            await page.evaluate(() => {
                const nativeScrollTo = window.scrollTo.bind(window);
                Object.defineProperty(window, "scrollTo", {
                    value: (options: ScrollToOptions) => {
                        document.body.dataset.scrollRequest =
                            JSON.stringify(options);
                        nativeScrollTo(options);
                    },
                });
            });
            await button.focus();
            await expect(button).toBeFocused();
            await page.keyboard.press(key);
            await expect(page.locator("body")).toHaveAttribute(
                "data-scroll-request",
                JSON.stringify({
                    top: 0,
                    behavior: reducedMotion === "reduce" ? "auto" : "smooth",
                })
            );
            await expect
                .poll(() => page.evaluate(() => window.scrollY))
                .toBe(0);
            await expect(button).toBeHidden();
        });
    }
}
