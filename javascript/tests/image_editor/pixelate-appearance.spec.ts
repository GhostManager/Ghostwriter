import { expect, test } from "@playwright/test";

test("four-border gradients blend into light, dark, tinted, and multicolor backgrounds", async ({
    page,
}) => {
    await page.goto("/");
    const examples = await page.evaluate(async () => {
        const result: { name: string; neutral: string; blended: string }[] = [];
        for (const [name, background, foreground] of [
            ["Light", "#ffffff", "#202428"],
            ["Dark", "#202830", "#e0e8f0"],
            ["Tinted", "#ece5d6", "#493f30"],
            ["Multiple border colors", "#ffffff", "#202428"],
        ]) {
            const canvas = document.createElement("canvas");
            canvas.width = 560;
            canvas.height = 150;
            const ctx = canvas.getContext("2d")!;
            ctx.fillStyle = background;
            ctx.fillRect(0, 0, 560, 150);
            if (name === "Multiple border colors") {
                const gradient = ctx.createLinearGradient(0, 0, 560, 150);
                gradient.addColorStop(0, "#bee3dc");
                gradient.addColorStop(0.4, "#efd4b4");
                gradient.addColorStop(0.7, "#d2d6f0");
                gradient.addColorStop(1, "#bee3dc");
                ctx.fillStyle = gradient;
                ctx.fillRect(0, 0, 560, 150);
            }
            ctx.fillStyle = foreground;
            ctx.font = "16px monospace";
            ctx.fillText("Connection details", 24, 32);
            ctx.font = "14px monospace";
            ctx.fillText("Account: demo-user", 24, 66);
            ctx.fillText("Token: SAMPLE-ONLY-123456", 24, 98);
            const source = canvas.toDataURL();
            const mask = {
                kind: "pixelate" as const,
                x0: 70,
                y0: 80,
                x1: 340,
                y1: 108,
            };
            result.push({
                name,
                neutral: await window.imageEditorTest.redact(source, [mask]),
                blended: await window.imageEditorTest.redact(source, [
                    { ...mask, blendWithBorder: true },
                ]),
            });
        }
        return result;
    });
    for (const example of examples)
        expect(example.blended).not.toBe(example.neutral);
    await page.evaluate((examples) => {
        document.body.replaceChildren();
        document.body.style.cssText =
            "margin:24px;background:#f3f5f7;color:#202428;font:16px sans-serif";
        const grid = document.createElement("main");
        grid.style.cssText =
            "display:grid;grid-template-columns:560px 560px;gap:14px 24px;width:max-content";
        for (const text of ["Neutral mosaic", "Border color + gradient"]) {
            const heading = document.createElement("strong");
            heading.textContent = text;
            grid.append(heading);
        }
        for (const example of examples)
            for (const mode of ["neutral", "blended"] as const) {
                const figure = document.createElement("figure");
                figure.style.margin = "0";
                const caption = document.createElement("figcaption");
                caption.textContent = example.name;
                caption.style.marginBottom = "6px";
                const image = document.createElement("img");
                image.src = example[mode];
                image.width = 560;
                image.height = 150;
                image.alt = `${example.name} ${mode}`;
                image.style.cssText =
                    "display:block;border:1px solid #dfe3e8;border-radius:8px";
                figure.append(caption, image);
                grid.append(figure);
            }
        document.body.append(grid);
    }, examples);
    await page.setViewportSize({ width: 1200, height: 650 });
    await expect(
        page.getByAltText("Tinted blended", { exact: true })
    ).toBeVisible();
    await page.screenshot({
        path: "../review/validation/pixelate-15px/appearance.png",
        fullPage: true,
    });
});
