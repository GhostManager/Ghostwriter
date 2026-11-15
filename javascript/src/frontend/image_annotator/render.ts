export type Tool =
    | "blackout"
    | "pixelate"
    | "rect"
    | "arrow"
    | "line"
    | "marker"
    | "pen"
    | "crop";

export type Region = { x0: number; y0: number; x1: number; y1: number };

export type BorderProfile = {
    readonly top: readonly (readonly number[])[];
    readonly bottom: readonly (readonly number[])[];
    readonly left: readonly (readonly number[])[];
    readonly right: readonly (readonly number[])[];
};

export type AnnotationOp =
    | ({ kind: "blackout" } & Region)
    | ({
          kind: "pixelate";
          blendWithBorder?: boolean;
          borderProfile?: BorderProfile;
      } & Region)
    | ({ kind: "crop" } & Region)
    | ({
          kind: "rect" | "arrow" | "line";
          color: string;
          width: number;
      } & Region)
    | {
          kind: "marker";
          x: number;
          y: number;
          number: number;
          color: string;
          radius: number;
      }
    | {
          kind: "pen";
          color: string;
          width: number;
          points: [number, number][];
      };

/** Stroke width that stays visible on both small crops and full-screen captures. */
export function defaultStrokeWidth(width: number, height: number): number {
    return Math.max(3, Math.round(Math.min(width, height) / 200));
}

/** Marker size scales with screenshots, while remaining legible on small images. */
export function markerRadius(width: number, height: number): number {
    return Math.min(
        Math.min(width, height) / 2,
        Math.max(12, Math.round(Math.min(width, height) / 30))
    );
}

/** History determines the next number, so undo, redo, and clear stay consistent. */
export function nextMarkerNumber(ops: readonly AnnotationOp[]): number {
    return ops.reduce(
        (next, op) =>
            op.kind === "marker" ? Math.max(next, op.number + 1) : next,
        1
    );
}

/** Snap lines to 45-degree steps or make a rectangle square, without leaving the image. */
export function constrainRegion(
    region: Region,
    kind: "line" | "arrow" | "rect",
    bounds?: { width: number; height: number }
): Region {
    const { x0, y0 } = region;
    let dx = region.x1 - x0;
    let dy = region.y1 - y0;
    if (kind === "rect") {
        const side = Math.max(Math.abs(dx), Math.abs(dy));
        dx = (dx < 0 ? -1 : 1) * side;
        dy = (dy < 0 ? -1 : 1) * side;
    } else if (dx !== 0 || dy !== 0) {
        const directions = [
            [1, 0],
            [1, 1],
            [0, 1],
            [-1, 1],
            [-1, 0],
            [-1, -1],
            [0, -1],
            [1, -1],
        ];
        const index = (Math.round(Math.atan2(dy, dx) / (Math.PI / 4)) + 8) % 8;
        const [ux, uy] = directions[index];
        const length = Math.hypot(dx, dy) / Math.hypot(ux, uy);
        dx = ux * length;
        dy = uy * length;
    }
    let scale = 1;
    if (bounds) {
        if (dx > 0) scale = Math.min(scale, (bounds.width - x0) / dx);
        if (dx < 0) scale = Math.min(scale, -x0 / dx);
        if (dy > 0) scale = Math.min(scale, (bounds.height - y0) / dy);
        if (dy < 0) scale = Math.min(scale, -y0 / dy);
    }
    scale = Math.max(0, scale);
    return { x0, y0, x1: x0 + dx * scale, y1: y0 + dy * scale };
}

/** Fixed source-pixel size shared by neutral and border-colored mosaics. */
const PIXEL_BLOCK_SIZE = 15;

/** The crop region in effect, if any. Each new crop replaces the previous one. */
export function activeCrop(
    ops: readonly AnnotationOp[]
): (Region & { kind: "crop" }) | null {
    for (let i = ops.length - 1; i >= 0; i--) {
        const op = ops[i];
        if (op.kind === "crop") return op;
    }
    return null;
}

/**
 * Render the image with every op applied, at the image's natural size.
 *
 * Crops are left out unless `applyCrop` is set, so the editor can keep showing the
 * whole image while a crop is pending.
 */
export function renderImage(
    image: CanvasImageSource & { naturalWidth: number; naturalHeight: number },
    ops: readonly AnnotationOp[],
    applyCrop = false,
    target?: HTMLCanvasElement
): HTMLCanvasElement {
    const canvas = target ?? document.createElement("canvas");
    if (canvas.width !== image.naturalWidth) canvas.width = image.naturalWidth;
    if (canvas.height !== image.naturalHeight)
        canvas.height = image.naturalHeight;
    const ctx = canvas.getContext("2d")!;
    // Reused backing storage must not retain removed annotations or pixels that
    // are transparent in the source, particularly after Undo or Clear.
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0);
    const redactions = ops.filter(
        (op) => op.kind === "blackout" || op.kind === "pixelate"
    );
    const selectedCrop = activeCrop(ops);
    // Resolve only unsnapshotted operations from the original source. Placed
    // UI operations always retain their captured visible-border profiles.
    const palettes = new Map<AnnotationOp, BorderProfile>();
    for (const op of redactions) {
        if (![op.x0, op.y0, op.x1, op.y1].every(Number.isFinite)) {
            throw new Error("Choose a finite redaction region.");
        }
    }
    for (const op of redactions) {
        if (op.kind === "pixelate" && op.blendWithBorder && !op.borderProfile) {
            palettes.set(
                op,
                sampleBorderProfile(ctx, op, redactions, selectedCrop)
            );
        }
    }
    for (const op of ops) {
        if (op.kind === "blackout" || op.kind === "pixelate") {
            const r = normalize(op, canvas);
            if (op.x0 === op.x1 || op.y0 === op.y1 || r.w < 1 || r.h < 1) {
                throw new Error(
                    "Choose a non-empty redaction area within the image."
                );
            }
        }
        drawOp(
            ctx,
            op,
            op.kind === "pixelate"
                ? (op.borderProfile ?? palettes.get(op))
                : undefined
        );
    }

    const crop = applyCrop ? selectedCrop : null;
    if (!crop) return canvas;
    try {
        return cropCanvas(canvas, crop);
    } finally {
        // A fresh full-size render is not needed once the cropped copy exists.
        // A caller-owned target stays usable for subsequent edits.
        if (!target) releaseCanvas(canvas);
    }
}

/** Copy a selected region at its original pixel dimensions, without resampling. */
export function cropCanvas(
    canvas: HTMLCanvasElement,
    crop: Region
): HTMLCanvasElement {
    if (
        ![crop.x0, crop.y0, crop.x1, crop.y1].every(Number.isFinite) ||
        crop.x0 === crop.x1 ||
        crop.y0 === crop.y1
    ) {
        throw new Error("Choose a crop with a positive width and height.");
    }
    const { x, y, w, h } = normalize(crop, canvas);
    if (w < 1 || h < 1) {
        throw new Error("The crop must overlap the image.");
    }
    const cropped = document.createElement("canvas");
    cropped.width = w;
    cropped.height = h;
    cropped.getContext("2d")!.drawImage(canvas, x, y, w, h, 0, 0, w, h);
    return cropped;
}

/** Drop a canvas's backing pixel storage as soon as its working copy is unused. */
export function releaseCanvas(canvas: HTMLCanvasElement) {
    canvas.width = 0;
    canvas.height = 0;
}

/** Dim everything outside `region` and outline it, to preview a crop. */
export function drawCropOverlay(
    ctx: CanvasRenderingContext2D,
    region: Region,
    lineWidth: number
) {
    const { x, y, w, h } = normalize(region, ctx.canvas);
    const { width, height } = ctx.canvas;
    ctx.save();
    ctx.fillStyle = "rgba(0, 0, 0, 0.55)";
    ctx.beginPath();
    ctx.rect(0, 0, width, height);
    ctx.rect(x, y, w, h);
    ctx.fill("evenodd");
    ctx.setLineDash([lineWidth * 2, lineWidth * 2]);
    ctx.lineWidth = Math.max(1, lineWidth / 2);
    ctx.strokeStyle = "#fff";
    ctx.strokeRect(x, y, w, h);
    ctx.restore();
}

/** Apply a single op on top of whatever is currently drawn in `ctx`. */
export function drawOp(
    ctx: CanvasRenderingContext2D,
    op: AnnotationOp,
    profile?: BorderProfile
) {
    switch (op.kind) {
        case "blackout":
        case "pixelate":
            censorRegion(
                ctx,
                op.kind,
                op,
                op.kind === "pixelate"
                    ? (op.borderProfile ?? profile)
                    : undefined
            );
            break;
        case "rect": {
            const r = normalize(op, ctx.canvas);
            ctx.save();
            ctx.strokeStyle = op.color;
            ctx.lineWidth = op.width;
            ctx.lineJoin = "miter";
            ctx.strokeRect(r.x, r.y, r.w, r.h);
            ctx.restore();
            break;
        }
        case "line":
            ctx.save();
            ctx.strokeStyle = op.color;
            ctx.lineWidth = op.width;
            ctx.lineCap = "round";
            ctx.beginPath();
            ctx.moveTo(op.x0, op.y0);
            ctx.lineTo(op.x1, op.y1);
            ctx.stroke();
            ctx.restore();
            break;
        case "marker":
            drawMarker(ctx, op);
            break;
        case "arrow":
            drawArrow(ctx, op);
            break;
        case "crop":
            // Applied by `renderImage` once every other op is drawn
            break;
        case "pen":
            ctx.save();
            ctx.strokeStyle = op.color;
            ctx.lineWidth = op.width;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.beginPath();
            op.points.forEach(([x, y], i) =>
                i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
            );
            ctx.stroke();
            ctx.restore();
            break;
    }
}

function normalize(r: Region, canvas: HTMLCanvasElement) {
    const x = Math.max(0, Math.floor(Math.min(r.x0, r.x1)));
    const y = Math.max(0, Math.floor(Math.min(r.y0, r.y1)));
    const right = Math.min(canvas.width, Math.ceil(Math.max(r.x0, r.x1)));
    const bottom = Math.min(canvas.height, Math.ceil(Math.max(r.y0, r.y1)));
    return { x, y, w: right - x, h: bottom - y };
}

const NEUTRAL_MOSAIC_COLOR = [112, 120, 128] as const;

/** Capture a placed region once; subsequent operations never resample its colors. */
export function freezePixelate(
    op: Extract<AnnotationOp, { kind: "pixelate" }>,
    source: HTMLCanvasElement,
    crop: Region | null
): Extract<AnnotationOp, { kind: "pixelate" }> {
    if (!op.blendWithBorder || op.borderProfile) return op;
    const profile = sampleBorderProfile(
        source.getContext("2d")!,
        op,
        [op],
        crop
    );
    const copy = (side: readonly (readonly number[])[]) =>
        Object.freeze(side.map((color) => Object.freeze([...color])));
    return {
        ...op,
        borderProfile: Object.freeze({
            top: copy(profile.top),
            bottom: copy(profile.bottom),
            left: copy(profile.left),
            right: copy(profile.right),
        }),
    };
}

/** Keep separate color segments on all four exterior borders. */
function sampleBorderProfile(
    ctx: CanvasRenderingContext2D,
    region: Region,
    redactions: readonly Region[],
    crop: Region | null
): BorderProfile {
    const { x, y, w, h } = normalize(region, ctx.canvas);
    const excluded = redactions.map((r) => normalize(r, ctx.canvas));
    const visible = crop ? normalize(crop, ctx.canvas) : null;
    const contains = (
        r: ReturnType<typeof normalize>,
        px: number,
        py: number
    ) => px >= r.x && px < r.x + r.w && py >= r.y && py < r.y + r.h;
    // Use a small exterior band so isolated colored text fringes do not
    // become the background color of an entire mosaic tile.
    const band = 4;
    const strips = [
        { x, y: Math.max(0, y - band), w, h: Math.min(band, y) },
        {
            x,
            y: y + h,
            w,
            h: Math.max(0, Math.min(band, ctx.canvas.height - y - h)),
        },
        { x: Math.max(0, x - band), y, w: Math.min(band, x), h },
        {
            x: x + w,
            y,
            w: Math.max(0, Math.min(band, ctx.canvas.width - x - w)),
            h,
        },
    ];
    const sides = strips.map((strip, edge) => {
        const horizontal = edge < 2;
        const length = horizontal ? strip.w : strip.h;
        const area = strip.w * strip.h;
        const count = Math.max(4, Math.min(8, Math.ceil(length / 48)));
        const buckets = Array.from(
            { length: count },
            () => new Map<number, { count: number; sum: number[] }>()
        );
        if (
            strip.w > 0 &&
            strip.h > 0 &&
            strip.x >= 0 &&
            strip.y >= 0 &&
            strip.x + strip.w <= ctx.canvas.width &&
            strip.y + strip.h <= ctx.canvas.height
        ) {
            const pixels = ctx.getImageData(
                strip.x,
                strip.y,
                strip.w,
                strip.h
            ).data;
            for (let i = 0; i < area; i++) {
                const px = strip.x + (i % strip.w),
                    py = strip.y + Math.floor(i / strip.w);
                if (
                    pixels[i * 4 + 3] !== 255 ||
                    (visible && !contains(visible, px, py)) ||
                    excluded.some((r) => contains(r, px, py))
                )
                    continue;
                const rgb = [
                    pixels[i * 4],
                    pixels[i * 4 + 1],
                    pixels[i * 4 + 2],
                ];
                const key =
                    ((rgb[0] >> 4) << 8) | ((rgb[1] >> 4) << 4) | (rgb[2] >> 4);
                const bucket =
                    buckets[
                        Math.min(
                            count - 1,
                            Math.floor(
                                ((horizontal
                                    ? i % strip.w
                                    : Math.floor(i / strip.w)) *
                                    count) /
                                    length
                            )
                        )
                    ];
                const value = bucket.get(key) ?? { count: 0, sum: [0, 0, 0] };
                value.count++;
                rgb.forEach((v, c) => (value.sum[c] += v));
                bucket.set(key, value);
            }
        }
        return buckets.map((bucket) => {
            const ranked = [...bucket.entries()].sort(
                (a, b) => b[1].count - a[1].count || a[0] - b[0]
            );
            let dominant = ranked[0]?.[1];
            const total = ranked.reduce(
                (sum, entry) => sum + entry[1].count,
                0
            );
            if (dominant && dominant.count < total * 0.35) {
                const chroma = (value: { count: number; sum: number[] }) =>
                    (Math.max(...value.sum) - Math.min(...value.sum)) /
                    value.count;
                // In a busy text edge, prefer a supported neutral background
                // over a low-frequency colored anti-aliasing fringe. Broad,
                // genuinely colored backgrounds still keep their own hue.
                if (chroma(dominant) > 12) {
                    dominant =
                        ranked.find(([, value]) => chroma(value) <= 12)?.[1] ??
                        dominant;
                }
            }
            return dominant
                ? dominant.sum.map((v) => Math.round(v / dominant.count))
                : null;
        });
    });
    const available = sides
        .flat()
        .filter((color): color is number[] => color !== null);
    const fallback = available.length
        ? [0, 1, 2].map(
              (c) =>
                  available.reduce((sum, color) => sum + color[c], 0) /
                  available.length
          )
        : [...NEUTRAL_MOSAIC_COLOR];
    const filled = sides.map((side) =>
        side.map((color, i) => {
            if (color) return [...color];
            let left = i - 1,
                right = i + 1;
            while (left >= 0 && !side[left]) left--;
            while (right < side.length && !side[right]) right++;
            if (left >= 0 && right < side.length)
                return mix(
                    side[left]!,
                    side[right]!,
                    (i - left) / (right - left)
                );
            return [...(side[left] ?? side[right] ?? fallback)];
        })
    );
    const [top, bottom, left, right] = filled;
    // Adjacent sides meet at shared corners, preventing seams in interpolation.
    for (const [a, ai, b, bi] of [
        [top, 0, left, 0],
        [top, top.length - 1, right, 0],
        [bottom, 0, left, left.length - 1],
        [bottom, bottom.length - 1, right, right.length - 1],
    ] as const) {
        const corner = mix(a[ai], b[bi], 0.5);
        a[ai] = [...corner];
        b[bi] = [...corner];
    }
    return { top, bottom, left, right };
}

function mix(a: readonly number[], b: readonly number[], t: number): number[] {
    return a.map((v, c) => v * (1 - t) + b[c] * t);
}
function sideColor(side: readonly (readonly number[])[], t: number): number[] {
    const position = Math.max(0, Math.min(1, t)) * (side.length - 1),
        index = Math.floor(position);
    return mix(
        side[index],
        side[Math.min(index + 1, side.length - 1)],
        position - index
    );
}
/** Blend border colors with positive weights, preventing subtractive hue overshoot. */
function borderGradient(
    profile: BorderProfile,
    u: number,
    v: number
): number[] {
    const colors = [
        sideColor(profile.top, u),
        sideColor(profile.bottom, u),
        sideColor(profile.left, v),
        sideColor(profile.right, v),
    ];
    if (v <= 0) return colors[0];
    if (v >= 1) return colors[1];
    if (u <= 0) return colors[2];
    if (u >= 1) return colors[3];
    const weights = [
        1 / (v * v),
        1 / ((1 - v) * (1 - v)),
        1 / (u * u),
        1 / ((1 - u) * (1 - u)),
    ];
    const total = weights.reduce((sum, weight) => sum + weight, 0);
    return [0, 1, 2].map((channel) =>
        Math.round(
            colors.reduce(
                (sum, color, edge) => sum + color[channel] * weights[edge],
                0
            ) / total
        )
    );
}

/** Quantize the four-border blend into uniform, opaque, solid-color tiles. */
function drawBorderMosaic(
    ctx: CanvasRenderingContext2D,
    r: ReturnType<typeof normalize>,
    profile: BorderProfile
) {
    const { x, y, w, h } = r;
    const block = PIXEL_BLOCK_SIZE;
    const columns = Math.ceil(w / block),
        rows = Math.ceil(h / block);
    for (let row = 0; row < rows; row++) {
        for (let col = 0; col < columns; col++) {
            const tileWidth = Math.min(block, w - col * block);
            const tileHeight = Math.min(block, h - row * block);
            const left = col === 0,
                right = col === columns - 1;
            const top = row === 0,
                bottom = row === rows - 1;
            const u = left ? 0 : right ? 1 : (col * block + tileWidth / 2) / w;
            const v = top ? 0 : bottom ? 1 : (row * block + tileHeight / 2) / h;
            const color = borderGradient(profile, u, v);
            const tile =
                (Math.imul(col + 1, 73856093) ^
                    Math.imul(row + 1, 19349663)) >>>
                0;
            const corner = (left || right) && (top || bottom);
            const shade = corner
                ? 0
                : ((tile % 5) - 2) * (left || right || top || bottom ? 4 : 8);
            ctx.fillStyle = `rgb(${color.map((value) => Math.round(Math.max(0, Math.min(255, value + shade)))).join(",")})`;
            ctx.fillRect(
                x + col * block,
                y + row * block,
                tileWidth,
                tileHeight
            );
        }
    }
}

/** Replace selected pixels; gradient and tiles never use the covered content. */
function censorRegion(
    ctx: CanvasRenderingContext2D,
    kind: "blackout" | "pixelate",
    region: Region,
    profile?: BorderProfile
) {
    if (![region.x0, region.y0, region.x1, region.y1].every(Number.isFinite)) {
        throw new Error("Choose a finite redaction region.");
    }
    const { x, y, w, h } = normalize(region, ctx.canvas);
    if (w < 1 || h < 1) return;
    const base = kind === "pixelate" ? NEUTRAL_MOSAIC_COLOR : [0, 0, 0];
    const rgb = (values: readonly number[]) => `rgb(${values.join(",")})`;
    ctx.save();
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
    ctx.fillStyle = rgb(base);
    ctx.fillRect(x, y, w, h);
    if (kind === "pixelate" && profile) {
        drawBorderMosaic(ctx, { x, y, w, h }, profile);
        ctx.restore();
        return;
    }
    if (kind === "pixelate") {
        const block = PIXEL_BLOCK_SIZE;
        for (let row = 0; row * block < h; row++) {
            for (let col = 0; col * block < w; col++) {
                // Geometry-only variation; never average or downsample secret pixels.
                const tile =
                    (Math.imul(col + 1, 73856093) ^
                        Math.imul(row + 1, 19349663)) >>>
                    0;
                const shade = ((tile % 5) - 2) * 12;
                ctx.fillStyle = rgb(
                    base.map((value) =>
                        Math.round(Math.max(0, Math.min(255, value + shade)))
                    )
                );
                ctx.fillRect(
                    x + col * block,
                    y + row * block,
                    Math.min(block, w - col * block),
                    Math.min(block, h - row * block)
                );
            }
        }
    }
    ctx.restore();
}

function drawArrow(
    ctx: CanvasRenderingContext2D,
    op: Region & { color: string; width: number }
) {
    const angle = Math.atan2(op.y1 - op.y0, op.x1 - op.x0);
    const head = op.width * 4;
    // Stop the shaft at the base of the head so the tip stays sharp
    const baseX = op.x1 - Math.cos(angle) * head * 0.8;
    const baseY = op.y1 - Math.sin(angle) * head * 0.8;

    ctx.save();
    ctx.strokeStyle = op.color;
    ctx.fillStyle = op.color;
    ctx.lineWidth = op.width;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(op.x0, op.y0);
    ctx.lineTo(baseX, baseY);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(op.x1, op.y1);
    ctx.lineTo(
        op.x1 - head * Math.cos(angle - Math.PI / 7),
        op.y1 - head * Math.sin(angle - Math.PI / 7)
    );
    ctx.lineTo(
        op.x1 - head * Math.cos(angle + Math.PI / 7),
        op.y1 - head * Math.sin(angle + Math.PI / 7)
    );
    ctx.closePath();
    ctx.fill();
    ctx.restore();
}

/** Flatten a numbered circle using locally available fonts and contrasting text. */
function drawMarker(
    ctx: CanvasRenderingContext2D,
    op: Extract<AnnotationOp, { kind: "marker" }>
) {
    const rgb = /^#([0-9a-f]{6})$/i.exec(op.color)?.[1] ?? "e00000";
    const channels = [0, 2, 4].map((offset) => {
        const component = parseInt(rgb.slice(offset, offset + 2), 16) / 255;
        return component <= 0.04045
            ? component / 12.92
            : ((component + 0.055) / 1.055) ** 2.4;
    });
    const luminance =
        channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    const ink = luminance > 0.179 ? "#000000" : "#ffffff";
    ctx.save();
    ctx.fillStyle = op.color;
    ctx.strokeStyle = ink;
    ctx.lineWidth = Math.max(1, op.radius / 12);
    ctx.beginPath();
    ctx.arc(op.x, op.y, op.radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    const label = String(op.number);
    let fontSize = op.radius * 1.25;
    ctx.font = `bold ${fontSize}px sans-serif`;
    const labelWidth = ctx.measureText(label).width;
    if (labelWidth > op.radius * 1.5)
        fontSize *= (op.radius * 1.5) / labelWidth;
    ctx.font = `bold ${fontSize}px sans-serif`;
    ctx.fillStyle = ink;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, op.x, op.y);
    ctx.restore();
}
