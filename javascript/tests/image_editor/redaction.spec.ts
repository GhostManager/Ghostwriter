import { expect, test } from "@playwright/test";

// The security contract is equality across different secrets, not OCR failure.
for (const blendWithBorder of [false, true])
    for (const region of [
        { x0: 10, y0: 10, x1: 70, y1: 40 },
        { x0: 70, y0: 40, x1: 10, y1: 10 },
        { x0: 10.8, y0: 10.2, x1: 70.1, y1: 40.7 },
        { x0: 0, y0: 0, x1: 96, y1: 64 },
        { x0: -10, y0: -20, x1: 1, y1: 1 },
        { x0: 95, y0: 63, x1: 120, y1: 90 },
    ]) {
        test(`pixelate ${blendWithBorder ? "border" : "neutral"} output is independent of secret pixels: ${JSON.stringify(region)}`, async ({
            page,
        }) => {
            await page.goto("/");
            const result = await page.evaluate(
                async ({ region, blendWithBorder }) => {
                    const x = Math.max(
                        0,
                        Math.floor(Math.min(region.x0, region.x1))
                    );
                    const y = Math.max(
                        0,
                        Math.floor(Math.min(region.y0, region.y1))
                    );
                    const right = Math.min(
                        96,
                        Math.ceil(Math.max(region.x0, region.x1))
                    );
                    const bottom = Math.min(
                        64,
                        Math.ceil(Math.max(region.y0, region.y1))
                    );
                    const sources: string[] = [];
                    const outputs: string[] = [];
                    for (let variant = 0; variant < 3; variant++) {
                        const canvas = document.createElement("canvas");
                        canvas.width = 96;
                        canvas.height = 64;
                        const ctx = canvas.getContext("2d")!;
                        ctx.fillStyle = "#e8d0b8";
                        ctx.fillRect(0, 0, 96, 64);
                        for (let py = y; py < bottom; py++)
                            for (let px = x; px < right; px++) {
                                ctx.clearRect(px, py, 1, 1);
                                ctx.fillStyle =
                                    variant === 0
                                        ? "#000"
                                        : variant === 1
                                          ? "#fff"
                                          : `rgba(${(px * 13) % 256},${(py * 19) % 256},255,0.3)`;
                                ctx.fillRect(px, py, 1, 1);
                            }
                        sources.push(canvas.toDataURL());
                        outputs.push(
                            await window.imageEditorTest.redact(
                                sources[variant],
                                [
                                    {
                                        kind: "pixelate",
                                        blendWithBorder,
                                        ...region,
                                    },
                                ]
                            )
                        );
                    }
                    const image = await createImageBitmap(
                        await (await fetch(outputs[0])).blob()
                    );
                    const canvas = document.createElement("canvas");
                    canvas.width = 96;
                    canvas.height = 64;
                    const ctx = canvas.getContext("2d")!;
                    ctx.drawImage(image, 0, 0);
                    image.close();
                    const pixels = ctx.getImageData(0, 0, 96, 64).data;
                    let opaque = true,
                        outsideUnchanged = true;
                    const colors = new Set<string>();
                    for (let py = 0; py < 64; py++)
                        for (let px = 0; px < 96; px++) {
                            const i = (py * 96 + px) * 4;
                            const rgba = pixels.subarray(i, i + 4);
                            if (
                                px >= x &&
                                px < right &&
                                py >= y &&
                                py < bottom
                            ) {
                                opaque &&= rgba[3] === 255;
                                colors.add(rgba.join(","));
                            } else
                                outsideUnchanged &&=
                                    rgba.join(",") === "232,208,184,255";
                        }
                    return {
                        differentInputs: sources[0] !== sources[1],
                        sameOutputs: outputs.every((png) => png === outputs[0]),
                        opaque,
                        outsideUnchanged,
                        colors: colors.size,
                    };
                },
                { region, blendWithBorder }
            );
            expect(result.differentInputs).toBe(true);
            expect(result.sameOutputs).toBe(true);
            expect(result.opaque).toBe(true);
            expect(result.outsideUnchanged).toBe(true);
            if (region.x1 - region.x0 > 30)
                expect(result.colors).toBeGreaterThan(1);
        });
    }

for (const relationship of [
    "adjacent",
    "overlapping",
    "nested",
    "saved sessions",
] as const) {
    test(`pixelate cannot transfer secret colors through ${relationship} redactions`, async ({
        page,
    }) => {
        await page.goto("/");
        const result = await page.evaluate(async (relationship) => {
            const a = {
                kind: "pixelate" as const,
                x0: 10,
                y0: 10,
                x1: 30,
                y1: 20,
            };
            const b = {
                kind: "pixelate" as const,
                x0: relationship === "nested" ? 12 : 10,
                y0: relationship === "nested" ? 12 : 9,
                x1: relationship === "nested" ? 20 : 31,
                y1:
                    relationship === "nested"
                        ? 18
                        : relationship === "adjacent"
                          ? 10
                          : 12,
            };
            const outputs: string[] = [];
            for (const secret of ["black", "white", "red"]) {
                const canvas = document.createElement("canvas");
                canvas.width = 96;
                canvas.height = 64;
                const ctx = canvas.getContext("2d")!;
                for (let y = 0; y < 64; y++)
                    for (let x = 0; x < 96; x++) {
                        ctx.fillStyle = (x + y) % 2 ? "black" : "white";
                        ctx.fillRect(x, y, 1, 1);
                    }
                ctx.fillStyle = secret;
                ctx.fillRect(b.x0, b.y0, b.x1 - b.x0, b.y1 - b.y0);
                let source = canvas.toDataURL();
                if (relationship === "saved sessions") {
                    source = await window.imageEditorTest.redact(source, [a]);
                    outputs.push(
                        await window.imageEditorTest.redact(source, [b])
                    );
                } else
                    outputs.push(
                        await window.imageEditorTest.redact(source, [a, b])
                    );
            }
            return outputs.every((png) => png === outputs[0]);
        }, relationship);
        expect(result).toBe(true);
    });
}

test("cropped-away colors cannot influence pixelate and transparent borders cannot preserve alpha", async ({
    page,
}) => {
    await page.goto("/");
    const same = await page.evaluate(async () => {
        const outputs: string[] = [];
        for (const border of ["black", "white", "rgba(100,200,50,0.2)"]) {
            const canvas = document.createElement("canvas");
            canvas.width = 96;
            canvas.height = 64;
            const ctx = canvas.getContext("2d")!;
            ctx.fillStyle = border;
            ctx.fillRect(0, 0, 96, 64);
            ctx.clearRect(10, 10, 30, 30);
            outputs.push(
                await window.imageEditorTest.redact(canvas.toDataURL(), [
                    { kind: "pixelate", x0: 10, y0: 10, x1: 40, y1: 40 },
                    { kind: "crop", x0: 10, y0: 10, x1: 40, y1: 40 },
                ])
            );
        }
        return outputs.every((png) => png === outputs[0]);
    });
    expect(same).toBe(true);
});

test("invalid redaction coordinates reject export rather than keeping source pixels", async ({
    page,
}) => {
    await page.goto("/");
    for (const value of [NaN, Infinity, -Infinity]) {
        const error = await page.evaluate(async (value) => {
            try {
                await window.imageEditorTest.redact(
                    window.imageEditorTest.fixture(),
                    [{ kind: "pixelate", x0: value, y0: 0, x1: 40, y1: 40 }]
                );
                return null;
            } catch (error) {
                return (error as Error).message;
            }
        }, value);
        expect(error).toContain("finite redaction region");
    }
});

test("invalid committed redaction areas reject export", async ({ page }) => {
    await page.goto("/");
    for (const region of [
        { x0: 20, y0: 10, x1: 20, y1: 30 },
        { x0: 20.5, y0: 10, x1: 20.5, y1: 30 },
        { x0: 20, y0: 10, x1: 30, y1: 10 },
        { x0: -20, y0: 10, x1: -10, y1: 30 },
        { x0: 401, y0: 10, x1: 410, y1: 30 },
    ]) {
        const error = await page.evaluate(async (region) => {
            try {
                await window.imageEditorTest.redact(
                    window.imageEditorTest.fixture(),
                    [{ kind: "pixelate", ...region }]
                );
                return null;
            } catch (error) {
                return (error as Error).message;
            }
        }, region);
        expect(error).toContain("non-empty redaction area");
    }
});

test("reapplying a pixelate mask to an already saved image is idempotent", async ({
    page,
}) => {
    await page.goto("/");
    const same = await page.evaluate(async () => {
        const ops = [
            { kind: "pixelate" as const, x0: 20, y0: 10, x1: 120, y1: 80 },
        ];
        const first = await window.imageEditorTest.redact(
            window.imageEditorTest.fixture(),
            ops
        );
        const second = await window.imageEditorTest.redact(first, ops);
        return first === second;
    });
    expect(same).toBe(true);
});

test("uniform borders produce opaque border-colored mosaic blocks", async ({
    page,
}) => {
    await page.goto("/");
    const result = await page.evaluate(async () => {
        const canvas = document.createElement("canvas");
        canvas.width = 160;
        canvas.height = 100;
        const ctx = canvas.getContext("2d")!;
        ctx.fillStyle = "#dbc9af";
        ctx.fillRect(0, 0, 160, 100);
        ctx.fillStyle = "magenta";
        ctx.fillRect(20, 20, 120, 60);
        const png = await window.imageEditorTest.redact(canvas.toDataURL(), [
            {
                kind: "pixelate",
                blendWithBorder: true,
                x0: 20,
                y0: 20,
                x1: 140,
                y1: 80,
            },
        ]);
        const image = await createImageBitmap(await (await fetch(png)).blob());
        ctx.clearRect(0, 0, 160, 100);
        ctx.drawImage(image, 0, 0);
        image.close();
        const pixels = ctx.getImageData(20, 20, 120, 60).data;
        let opaque = true,
            beige = true,
            edge = 0,
            center = 0,
            edgeCount = 0,
            centerCount = 0;
        for (let y = 0; y < 60; y++)
            for (let x = 0; x < 120; x++) {
                const i = (y * 120 + x) * 4;
                opaque &&= pixels[i + 3] === 255;
                beige &&=
                    pixels[i] > pixels[i + 1] && pixels[i + 1] > pixels[i + 2];
                if (x < 10 || x >= 110 || y < 10 || y >= 50) {
                    edge += pixels[i];
                    edgeCount++;
                }
                if (x >= 40 && x < 80 && y >= 20 && y < 40) {
                    center += pixels[i];
                    centerCount++;
                }
            }
        return {
            edgesMatch: [
                [20, 20],
                [139, 20],
                [20, 79],
                [139, 79],
            ].every(
                ([x, y]) =>
                    [...ctx.getImageData(x, y, 1, 1).data].join(",") ===
                    "219,201,175,255"
            ),
            opaque,
            beige,
            edge: edge / edgeCount,
            center: center / centerCount,
        };
    });
    expect(result.opaque).toBe(true);
    expect(result.edgesMatch).toBe(true);
    expect(result.beige).toBe(true);
    expect(result.edge).toBeGreaterThan(210);
});

for (const overlap of [false, true]) {
    test(`border blending excludes later ${overlap ? "overlapping" : "adjacent"} redactions`, async ({
        page,
    }) => {
        await page.goto("/");
        const same = await page.evaluate(async (overlap) => {
            const outputs: string[] = [];
            for (const secret of ["black", "white", "red"]) {
                const canvas = document.createElement("canvas");
                canvas.width = 96;
                canvas.height = 64;
                const ctx = canvas.getContext("2d")!;
                for (let y = 0; y < 64; y++)
                    for (let x = 0; x < 96; x++) {
                        ctx.fillStyle = (x + y) % 2 ? "black" : "white";
                        ctx.fillRect(x, y, 1, 1);
                    }
                ctx.fillStyle = secret;
                ctx.fillRect(10, 9, 21, overlap ? 3 : 1);
                outputs.push(
                    await window.imageEditorTest.redact(canvas.toDataURL(), [
                        {
                            kind: "pixelate",
                            blendWithBorder: true,
                            x0: 10,
                            y0: 10,
                            x1: 30,
                            y1: 20,
                        },
                        {
                            kind: "pixelate",
                            blendWithBorder: true,
                            x0: 10,
                            y0: 9,
                            x1: 31,
                            y1: overlap ? 12 : 10,
                        },
                    ])
                );
            }
            return outputs.every((png) => png === outputs[0]);
        }, overlap);
        expect(same).toBe(true);
    });
}

test("border blending ignores cropped-away colors and falls back on transparent borders", async ({
    page,
}) => {
    await page.goto("/");
    const result = await page.evaluate(async () => {
        const cropped: string[] = [],
            transparent: string[] = [];
        for (const color of ["black", "white", "rgba(100,200,50,0.2)"]) {
            const canvas = document.createElement("canvas");
            canvas.width = 96;
            canvas.height = 64;
            const ctx = canvas.getContext("2d")!;
            ctx.fillStyle = color;
            ctx.fillRect(0, 0, 96, 64);
            ctx.fillStyle = "red";
            ctx.fillRect(10, 10, 30, 30);
            const op = {
                kind: "pixelate" as const,
                blendWithBorder: true,
                x0: 10,
                y0: 10,
                x1: 40,
                y1: 40,
            };
            cropped.push(
                await window.imageEditorTest.redact(canvas.toDataURL(), [
                    op,
                    { kind: "crop", x0: 10, y0: 10, x1: 40, y1: 40 },
                ])
            );
            ctx.clearRect(0, 0, 96, 64);
            ctx.fillStyle = color;
            ctx.fillRect(10, 10, 30, 30);
            const png = await window.imageEditorTest.redact(
                canvas.toDataURL(),
                [op]
            );
            const image = await createImageBitmap(
                await (await fetch(png)).blob()
            );
            ctx.clearRect(0, 0, 96, 64);
            ctx.drawImage(image, 0, 0);
            image.close();
            transparent.push(ctx.getImageData(10, 10, 30, 30).data.join(","));
        }
        return {
            crop: cropped.every((png) => png === cropped[0]),
            fallback: transparent.every((pixels) => pixels === transparent[0]),
        };
    });
    expect(result).toEqual({ crop: true, fallback: true });
});

test("wide selections preserve different colors on their short and long borders", async ({
    page,
}) => {
    await page.goto("/");
    const pixel = await page.evaluate(async () => {
        const canvas = document.createElement("canvas");
        canvas.width = 1600;
        canvas.height = 220;
        const ctx = canvas.getContext("2d")!;
        ctx.fillStyle = "#dbc9af";
        ctx.fillRect(0, 0, 1600, 220);
        ctx.fillStyle = "black";
        ctx.fillRect(96, 30, 4, 160);
        ctx.fillRect(1500, 30, 4, 160);
        const png = await window.imageEditorTest.redact(canvas.toDataURL(), [
            {
                kind: "pixelate",
                blendWithBorder: true,
                x0: 100,
                y0: 30,
                x1: 1500,
                y1: 190,
            },
        ]);
        const image = await createImageBitmap(await (await fetch(png)).blob());
        ctx.drawImage(image, 0, 0);
        image.close();
        return [
            [700, 30],
            [100, 110],
            [1499, 110],
        ].map(([x, y]) => [...ctx.getImageData(x, y, 1, 1).data]);
    });
    const expected = [
        [219, 201, 175],
        [0, 0, 0],
        [0, 0, 0],
    ];
    pixel.forEach((color, edge) => {
        expect(color[3]).toBe(255);
        expected[edge].forEach((value, channel) =>
            expect(Math.abs(color[channel] - value)).toBeLessThanOrEqual(8)
        );
    });
});

test("four-edge interpolation preserves distinct colors and segments along every border", async ({
    page,
}) => {
    await page.goto("/");
    const result = await page.evaluate(async () => {
        const canvas = document.createElement("canvas");
        canvas.width = 200;
        canvas.height = 160;
        const ctx = canvas.getContext("2d")!;
        ctx.fillStyle = "magenta";
        ctx.fillRect(0, 0, 200, 160);
        ctx.fillStyle = "red";
        ctx.fillRect(20, 16, 80, 4);
        ctx.fillStyle = "cyan";
        ctx.fillRect(100, 16, 80, 4);
        ctx.fillStyle = "blue";
        ctx.fillRect(20, 140, 80, 4);
        ctx.fillStyle = "white";
        ctx.fillRect(100, 140, 80, 4);
        ctx.fillStyle = "lime";
        ctx.fillRect(16, 20, 4, 60);
        ctx.fillStyle = "black";
        ctx.fillRect(16, 80, 4, 60);
        ctx.fillStyle = "yellow";
        ctx.fillRect(180, 20, 4, 60);
        ctx.fillStyle = "gray";
        ctx.fillRect(180, 80, 4, 60);
        const op = {
            kind: "pixelate" as const,
            blendWithBorder: true,
            x0: 20,
            y0: 20,
            x1: 180,
            y1: 140,
        };
        const frozen = await window.imageEditorTest.freeze(
            canvas.toDataURL(),
            op
        );
        const png = await window.imageEditorTest.redact(canvas.toDataURL(), [
            frozen,
        ]);
        const image = await createImageBitmap(await (await fetch(png)).blob());
        ctx.drawImage(image, 0, 0);
        image.close();
        const positions = [
            [60, 20],
            [140, 20],
            [60, 139],
            [140, 139],
            [20, 50],
            [20, 110],
            [179, 50],
            [179, 110],
        ];
        return {
            edges: positions.map(([x, y]) => [
                ...ctx.getImageData(x, y, 1, 1).data,
            ]),
            center: [...ctx.getImageData(100, 80, 1, 1).data],
        };
    });
    const expected = [
        [255, 0, 0],
        [0, 255, 255],
        [0, 0, 255],
        [255, 255, 255],
        [0, 255, 0],
        [0, 0, 0],
        [255, 255, 0],
        [128, 128, 128],
    ];
    // Solid 15px tiles sample each border segment at a representative position.
    result.edges.forEach((color, edge) => {
        expect(color[3]).toBe(255);
        expected[edge].forEach((value, channel) =>
            expect(Math.abs(color[channel] - value)).toBeLessThanOrEqual(64)
        );
    });
    expect(result.center[3]).toBe(255);
    expect(new Set(result.center.slice(0, 3)).size).toBeGreaterThan(1);
});

test("a frozen four-border profile ignores later changes to source borders and hidden pixels", async ({
    page,
}) => {
    await page.goto("/");
    const result = await page.evaluate(async () => {
        const canvas = document.createElement("canvas");
        canvas.width = 120;
        canvas.height = 100;
        const ctx = canvas.getContext("2d")!;
        ctx.fillStyle = "#b8d0e8";
        ctx.fillRect(0, 0, 120, 100);
        ctx.fillStyle = "#204080";
        ctx.fillRect(20, 19, 80, 1);
        const op = {
            kind: "pixelate" as const,
            blendWithBorder: true,
            x0: 20,
            y0: 20,
            x1: 100,
            y1: 80,
        };
        const frozen = await window.imageEditorTest.freeze(
            canvas.toDataURL(),
            op
        );
        const profile = JSON.stringify(frozen);
        const outputs: string[] = [];
        for (const color of ["black", "white", "rgba(255,0,255,0.2)"]) {
            ctx.clearRect(0, 0, 120, 100);
            ctx.fillStyle = color;
            ctx.fillRect(0, 0, 120, 100);
            outputs.push(
                await window.imageEditorTest.redact(canvas.toDataURL(), [
                    frozen,
                    { kind: "crop", x0: 20, y0: 20, x1: 100, y1: 80 },
                ])
            );
        }
        const decoded = await createImageBitmap(
            await (await fetch(outputs[0])).blob()
        );
        const check = document.createElement("canvas");
        check.width = decoded.width;
        check.height = decoded.height;
        check.getContext("2d")!.drawImage(decoded, 0, 0);
        decoded.close();
        const pixels = check
            .getContext("2d")!
            .getImageData(0, 0, check.width, check.height).data;
        return {
            same: outputs.every((png) => png === outputs[0]),
            unchanged: JSON.stringify(frozen) === profile,
            opaque: pixels.every((value, i) => i % 4 !== 3 || value === 255),
        };
    });
    expect(result).toEqual({ same: true, unchanged: true, opaque: true });
});

test("coarse mosaics use fewer color transitions and broad border segments", async ({
    page,
}) => {
    await page.goto("/");
    const result = await page.evaluate(async () => {
        const source = window.imageEditorTest.fixture();
        const op = {
            kind: "pixelate" as const,
            x0: 100,
            y0: 100,
            x1: 260,
            y1: 180,
        };
        const frozen = await window.imageEditorTest.freeze(source, {
            ...op,
            blendWithBorder: true,
        });
        const png = await window.imageEditorTest.redact(source, [op]);
        const image = await createImageBitmap(await (await fetch(png)).blob());
        const canvas = document.createElement("canvas");
        canvas.width = image.width;
        canvas.height = image.height;
        const ctx = canvas.getContext("2d")!;
        ctx.drawImage(image, 0, 0);
        image.close();
        const pixels = ctx.getImageData(100, 130, 160, 1).data;
        let runs = 1;
        for (let x = 1; x < 160; x++)
            if (pixels[x * 4] !== pixels[(x - 1) * 4]) runs++;
        if (frozen.kind !== "pixelate" || !frozen.borderProfile)
            throw new Error("Missing frozen border profile");
        return {
            runs,
            segments: Object.values(frozen.borderProfile).map(
                (side) => side.length
            ),
        };
    });
    expect(result.runs).toBeGreaterThan(1);
    expect(result.runs).toBeLessThanOrEqual(11);
    expect(result.segments.every((count) => count >= 4 && count <= 8)).toBe(
        true
    );
});

test("blue and gray borders never generate yellow from corner subtraction", async ({
    page,
}) => {
    await page.goto("/");
    const result = await page.evaluate(async () => {
        const side = [
            [0, 0, 255],
            [128, 128, 128],
            [0, 0, 255],
        ];
        const source = window.imageEditorTest.fixture();
        const png = await window.imageEditorTest.redact(source, [
            {
                kind: "pixelate",
                blendWithBorder: true,
                x0: 20,
                y0: 20,
                x1: 180,
                y1: 120,
                borderProfile: {
                    top: side,
                    bottom: side,
                    left: side,
                    right: side,
                },
            },
        ]);
        const image = await createImageBitmap(await (await fetch(png)).blob());
        const canvas = document.createElement("canvas");
        canvas.width = image.width;
        canvas.height = image.height;
        const ctx = canvas.getContext("2d")!;
        ctx.drawImage(image, 0, 0);
        image.close();
        const pixels = ctx.getImageData(20, 20, 160, 100).data;
        let noYellow = true,
            opaque = true;
        for (let i = 0; i < pixels.length; i += 4) {
            // Every sampled color has R=G<=B. Positive mixtures and neutral
            // texture preserve that property; subtracting blue corners does not.
            noYellow &&=
                pixels[i] === pixels[i + 1] && pixels[i] <= pixels[i + 2];
            opaque &&= pixels[i + 3] === 255;
        }
        return {
            noYellow,
            opaque,
            center: [...ctx.getImageData(100, 70, 1, 1).data],
        };
    });
    expect(result.noYellow).toBe(true);
    expect(result.opaque).toBe(true);
    expect(result.center[0]).toBeLessThan(160);
    expect(result.center[2]).toBeGreaterThanOrEqual(result.center[0]);
});

for (const blendWithBorder of [false, true]) {
    test(`${blendWithBorder ? "border-colored" : "neutral"} mosaic tiles stay solid and 15px across different image sizes`, async ({
        page,
    }) => {
        await page.goto("/");
        const result = await page.evaluate(async (blendWithBorder) => {
            const captures: string[] = [];
            let solid = true,
                opaque = true;
            for (const [width, height] of [
                [400, 300],
                [2048, 1024],
            ]) {
                const canvas = document.createElement("canvas");
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext("2d")!;
                ctx.fillStyle = "magenta";
                ctx.fillRect(0, 0, width, height);
                const profile = {
                    top: [
                        [255, 0, 0],
                        [0, 255, 255],
                    ],
                    bottom: [
                        [0, 0, 255],
                        [255, 255, 255],
                    ],
                    left: [
                        [255, 0, 0],
                        [0, 0, 255],
                    ],
                    right: [
                        [0, 255, 255],
                        [255, 255, 255],
                    ],
                };
                const png = await window.imageEditorTest.redact(
                    canvas.toDataURL(),
                    [
                        {
                            kind: "pixelate",
                            blendWithBorder,
                            x0: 20,
                            y0: 20,
                            x1: 180,
                            y1: 100,
                            ...(blendWithBorder
                                ? { borderProfile: profile }
                                : {}),
                        },
                    ]
                );
                const image = await createImageBitmap(
                    await (await fetch(png)).blob()
                );
                ctx.drawImage(image, 0, 0);
                image.close();
                const pixels = ctx.getImageData(20, 20, 160, 80).data;
                for (let y = 0; y < 80; y++)
                    for (let x = 0; x < 160; x++) {
                        const index = (y * 160 + x) * 4,
                            tile =
                                (Math.floor(y / 15) * 15 * 160 +
                                    Math.floor(x / 15) * 15) *
                                4;
                        solid &&= [0, 1, 2, 3].every(
                            (channel) =>
                                pixels[index + channel] ===
                                pixels[tile + channel]
                        );
                        opaque &&= pixels[index + 3] === 255;
                    }
                captures.push(pixels.join(","));
            }
            return {
                solid,
                opaque,
                sameSizeIndependentPixels: captures[0] === captures[1],
            };
        }, blendWithBorder);
        expect(result).toEqual({
            solid: true,
            opaque: true,
            sameSizeIndependentPixels: true,
        });
    });
}

test("colored single-pixel text fringes do not tint a dark background mosaic", async ({
    page,
}) => {
    await page.goto("/");
    const neutral = await page.evaluate(async () => {
        const canvas = document.createElement("canvas");
        canvas.width = 240;
        canvas.height = 160;
        const ctx = canvas.getContext("2d")!;
        ctx.fillStyle = "#181818";
        ctx.fillRect(0, 0, 240, 160);
        ctx.fillStyle = "cyan";
        ctx.fillRect(30, 29, 180, 1);
        ctx.fillStyle = "red";
        ctx.fillRect(30, 130, 180, 1);
        ctx.fillStyle = "#ff2020";
        ctx.fillRect(29, 30, 1, 100);
        ctx.fillStyle = "#20ffff";
        ctx.fillRect(210, 30, 1, 100);
        const op = {
            kind: "pixelate" as const,
            blendWithBorder: true,
            x0: 30,
            y0: 30,
            x1: 210,
            y1: 130,
        };
        const frozen = await window.imageEditorTest.freeze(
            canvas.toDataURL(),
            op
        );
        const png = await window.imageEditorTest.redact(canvas.toDataURL(), [
            frozen,
        ]);
        const image = await createImageBitmap(await (await fetch(png)).blob());
        ctx.drawImage(image, 0, 0);
        image.close();
        const pixels = ctx.getImageData(30, 30, 180, 100).data;
        for (let i = 0; i < pixels.length; i += 4)
            if (
                pixels[i] !== pixels[i + 1] ||
                pixels[i + 1] !== pixels[i + 2] ||
                pixels[i + 3] !== 255
            )
                return false;
        return true;
    });
    expect(neutral).toBe(true);
});
