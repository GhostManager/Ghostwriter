export type Tool =
    | "blackout"
    | "pixelate"
    | "blur"
    | "rect"
    | "arrow"
    | "pen"
    | "crop";

export type Region = { x0: number; y0: number; x1: number; y1: number };

export type AnnotationOp =
    | ({ kind: "blackout" | "pixelate" | "blur" } & Region)
    | ({ kind: "crop" } & Region)
    | ({ kind: "rect" | "arrow"; color: string; width: number } & Region)
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

/** Size of the blocks used by pixelate, scaled with the image so text stays unreadable. */
export function pixelBlockSize(width: number, height: number): number {
    return Math.max(10, Math.round(Math.min(width, height) / 50));
}

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
    applyCrop = false
): HTMLCanvasElement {
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(image, 0, 0);
    for (const op of ops) drawOp(ctx, op);

    const crop = applyCrop ? activeCrop(ops) : null;
    if (!crop) return canvas;
    const { x, y, w, h } = normalize(crop, canvas);
    if (w < 1 || h < 1) return canvas;
    const cropped = document.createElement("canvas");
    cropped.width = w;
    cropped.height = h;
    cropped.getContext("2d")!.drawImage(canvas, x, y, w, h, 0, 0, w, h);
    return cropped;
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
export function drawOp(ctx: CanvasRenderingContext2D, op: AnnotationOp) {
    switch (op.kind) {
        case "blackout":
        case "pixelate":
        case "blur":
            censorRegion(ctx, op.kind, op);
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

function censorRegion(
    ctx: CanvasRenderingContext2D,
    kind: "blackout" | "pixelate" | "blur",
    region: Region
) {
    const { x, y, w, h } = normalize(region, ctx.canvas);
    if (w < 1 || h < 1) return;

    if (kind === "blackout") {
        ctx.save();
        ctx.fillStyle = "#000";
        ctx.fillRect(x, y, w, h);
        ctx.restore();
        return;
    }

    const block = pixelBlockSize(ctx.canvas.width, ctx.canvas.height);
    // Blur averages over a wider area than pixelate so the result is smooth
    const factor = kind === "blur" ? block * 1.5 : block;
    const small = downsample(
        ctx.canvas,
        x,
        y,
        w,
        h,
        Math.max(1, Math.round(w / factor)),
        Math.max(1, Math.round(h / factor))
    );

    // Blur scales back up in steps so the bilinear filter doesn't leave visible blocks
    const result = kind === "blur" ? upsample(small, w, h) : small;

    ctx.save();
    ctx.beginPath();
    ctx.rect(x, y, w, h);
    ctx.clip();
    ctx.imageSmoothingEnabled = kind === "blur";
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(result, 0, 0, result.width, result.height, x, y, w, h);
    ctx.restore();
}

/** Grow `source` toward `tw`x`th` by doubling repeatedly with smoothing. */
function upsample(
    source: HTMLCanvasElement,
    tw: number,
    th: number
): HTMLCanvasElement {
    let current = source;
    while (current.width < tw || current.height < th) {
        const next = document.createElement("canvas");
        next.width = Math.min(tw, current.width * 2);
        next.height = Math.min(th, current.height * 2);
        const nctx = next.getContext("2d")!;
        nctx.imageSmoothingEnabled = true;
        nctx.imageSmoothingQuality = "high";
        nctx.drawImage(current, 0, 0, next.width, next.height);
        current = next;
    }
    return current;
}

/**
 * Shrink a region of `source` to `tw`x`th` by halving repeatedly, so every source pixel
 * contributes to the result instead of only the few sampled by a single large downscale.
 */
function downsample(
    source: HTMLCanvasElement,
    sx: number,
    sy: number,
    sw: number,
    sh: number,
    tw: number,
    th: number
): HTMLCanvasElement {
    let current = document.createElement("canvas");
    current.width = sw;
    current.height = sh;
    current.getContext("2d")!.drawImage(source, sx, sy, sw, sh, 0, 0, sw, sh);

    while (current.width > tw || current.height > th) {
        const next = document.createElement("canvas");
        next.width = Math.max(tw, Math.ceil(current.width / 2));
        next.height = Math.max(th, Math.ceil(current.height / 2));
        const nctx = next.getContext("2d")!;
        nctx.imageSmoothingEnabled = true;
        nctx.imageSmoothingQuality = "high";
        nctx.drawImage(current, 0, 0, next.width, next.height);
        current = next;
    }
    return current;
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
