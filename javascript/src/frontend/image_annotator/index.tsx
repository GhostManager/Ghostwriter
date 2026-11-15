import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faSquare as faSquareOutline } from "@fortawesome/free-regular-svg-icons/faSquare";
import { faArrowRightLong } from "@fortawesome/free-solid-svg-icons/faArrowRightLong";
import { faCropSimple } from "@fortawesome/free-solid-svg-icons/faCropSimple";
import { faEyeDropper } from "@fortawesome/free-solid-svg-icons/faEyeDropper";
import { faMinus } from "@fortawesome/free-solid-svg-icons/faMinus";
import { faCircle } from "@fortawesome/free-solid-svg-icons/faCircle";
import { faPen } from "@fortawesome/free-solid-svg-icons/faPen";
import { faRotateLeft } from "@fortawesome/free-solid-svg-icons/faRotateLeft";
import { faRotateRight } from "@fortawesome/free-solid-svg-icons/faRotateRight";
import { faSquare } from "@fortawesome/free-solid-svg-icons/faSquare";
import { faTableCells } from "@fortawesome/free-solid-svg-icons/faTableCells";
import { faTrashCan } from "@fortawesome/free-solid-svg-icons/faTrashCan";
import React, { useCallback, useEffect, useRef, useState } from "react";
import ReactModal from "react-modal";
import {
    activeCrop,
    AnnotationOp,
    constrainRegion,
    cropCanvas,
    defaultStrokeWidth,
    markerRadius,
    nextMarkerNumber,
    drawCropOverlay,
    drawOp,
    Region,
    renderImage,
    releaseCanvas,
    freezePixelate,
    Tool,
} from "./render";

type ToolGroup = "censor" | "highlight" | "adjust";

const GROUP_LABELS: Record<ToolGroup, string> = {
    censor: "Censor",
    highlight: "Highlight",
    adjust: "Adjust",
};

const TOOLS: {
    tool: Tool;
    label: string;
    icon: IconDefinition;
    group: ToolGroup;
}[] = [
    { tool: "blackout", label: "Black box", icon: faSquare, group: "censor" },
    {
        tool: "pixelate",
        label: "Pixelate",
        icon: faTableCells,
        group: "censor",
    },
    {
        tool: "rect",
        label: "Rectangle",
        icon: faSquareOutline,
        group: "highlight",
    },
    {
        tool: "arrow",
        label: "Arrow",
        icon: faArrowRightLong,
        group: "highlight",
    },
    { tool: "line", label: "Line", icon: faMinus, group: "highlight" },
    { tool: "pen", label: "Pen", icon: faPen, group: "highlight" },
    {
        tool: "marker",
        label: "Number marker",
        icon: faCircle,
        group: "highlight",
    },
    { tool: "crop", label: "Crop", icon: faCropSimple, group: "adjust" },
];

const COLORS = ["#e00000", "#ff9500", "#ffd400", "#00b050", "#0070c0"];

/**
 * Modal for censoring, drawing, numbered annotations, and cropping image evidence.
 * Colors can be chosen directly or sampled from the displayed image.
 *
 * All edits are flattened into the pixels of the exported PNG, so censored content
 * cannot be recovered by removing an overlay, and cropped-out areas are not kept.
 */
export default function ImageAnnotator(props: {
    /** URL or file of the image to edit */
    source: string | Blob;
    title?: string;
    saveLabel?: string;
    /** Extra text shown above the action buttons */
    notice?: React.ReactNode;
    onCancel: () => void;
    onSave: (image: Blob) => Promise<void>;
}) {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const setCanvas = useCallback((canvas: HTMLCanvasElement | null) => {
        if (!canvas && canvasRef.current) releaseCanvas(canvasRef.current);
        canvasRef.current = canvas;
    }, []);
    // Render of the image and committed ops, reused while an op is being drawn
    const committedRef = useRef<HTMLCanvasElement | null>(null);
    const draftRef = useRef<AnnotationOp | null>(null);
    const rawRegionRef = useRef<Region | null>(null);

    // One editing session always operates on the same source. Polling must not
    // silently rebase pending operations onto a collaborator's edited image.
    const [source] = useState(props.source);

    const [image, setImage] = useState<HTMLImageElement | null>(null);
    const [loadError, setLoadError] = useState(false);
    const [ops, setOps] = useState<AnnotationOp[]>([]);
    const [redoStack, setRedoStack] = useState<AnnotationOp[]>([]);
    const [tool, setTool] = useState<Tool>("blackout");
    const [color, setColor] = useState(COLORS[0]);
    const [colorText, setColorText] = useState(COLORS[0]);
    const [pickingColor, setPickingColor] = useState(false);
    const [blendWithBorder, setBlendWithBorder] = useState(true);
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState<string | null>(null);
    const [selectionError, setSelectionError] = useState<string | null>(null);

    useEffect(() => {
        let objectUrl: string | null = null;
        const src =
            typeof source === "string"
                ? source
                : (objectUrl = URL.createObjectURL(source));
        const img = new Image();
        img.onload = () => {
            setImage(img);
        };
        img.onerror = () => setLoadError(true);
        img.src = src;
        return () => {
            img.onload = img.onerror = null;
            img.removeAttribute("src");
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        };
    }, [source]);

    const strokeWidth = image
        ? defaultStrokeWidth(image.naturalWidth, image.naturalHeight)
        : 3;

    useEffect(() => setColorText(color), [color]);

    const paint = useCallback(() => {
        const canvas = canvasRef.current;
        const committed = committedRef.current;
        if (!canvas || !committed) return;
        const ctx = canvas.getContext("2d")!;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const draft = draftRef.current;
        ctx.drawImage(committed, 0, 0);
        if (draft && draft.kind !== "crop") {
            // Preview and placement sample the same visible committed layer.
            const preview =
                draft.kind === "pixelate"
                    ? freezePixelate(draft, committed, activeCrop(ops))
                    : draft;
            drawOp(ctx, preview);
            if (draft.kind === "blackout" || draft.kind === "pixelate") {
                // Outline the region so it's visible while dragging over dark areas
                ctx.save();
                ctx.setLineDash([strokeWidth * 2, strokeWidth * 2]);
                ctx.lineWidth = Math.max(1, strokeWidth / 2);
                ctx.strokeStyle = "#ff00ff";
                ctx.strokeRect(
                    Math.min(draft.x0, draft.x1),
                    Math.min(draft.y0, draft.y1),
                    Math.abs(draft.x1 - draft.x0),
                    Math.abs(draft.y1 - draft.y0)
                );
                ctx.restore();
            }
        }
        // Keep showing the whole image so a crop can be redrawn, but dim what will be cut
        const crop = draft?.kind === "crop" ? draft : activeCrop(ops);
        if (crop) drawCropOverlay(ctx, crop, strokeWidth);
    }, [strokeWidth, ops]);

    // Re-render the committed layer whenever the op list changes
    useEffect(() => {
        if (!image || !canvasRef.current) return;
        const canvas = canvasRef.current;
        if (canvas.width !== image.naturalWidth)
            canvas.width = image.naturalWidth;
        if (canvas.height !== image.naturalHeight)
            canvas.height = image.naturalHeight;
        committedRef.current = renderImage(
            image,
            ops,
            false,
            committedRef.current ?? undefined
        );
        paint();
    }, [image, ops, paint]);

    useEffect(() => {
        return () => {
            if (committedRef.current) releaseCanvas(committedRef.current);
            committedRef.current = null;
            draftRef.current = null;
            rawRegionRef.current = null;
        };
    }, []);

    const toImageCoords = (ev: React.PointerEvent<HTMLCanvasElement>) => {
        const canvas = ev.currentTarget;
        const rect = canvas.getBoundingClientRect();
        const x = ((ev.clientX - rect.left) * canvas.width) / rect.width;
        const y = ((ev.clientY - rect.top) * canvas.height) / rect.height;
        return {
            x: Math.max(0, Math.min(canvas.width, x)),
            y: Math.max(0, Math.min(canvas.height, y)),
        };
    };

    const sampleColor = (x: number, y: number) => {
        const canvas = committedRef.current;
        if (!canvas || saving) return;
        const pixel = canvas
            .getContext("2d")!
            .getImageData(
                Math.min(canvas.width - 1, Math.max(0, Math.floor(x))),
                Math.min(canvas.height - 1, Math.max(0, Math.floor(y))),
                1,
                1
            ).data;
        if (pixel[3] === 0) {
            setSelectionError(
                "Choose a visible image pixel to sample its color."
            );
            return;
        }
        setColor(
            "#" +
                Array.from(pixel.subarray(0, 3), (value) =>
                    value.toString(16).padStart(2, "0")
                ).join("")
        );
        setPickingColor(false);
        setSelectionError(null);
    };

    const makeMarker = (
        x: number,
        y: number,
        number: number
    ): Extract<AnnotationOp, { kind: "marker" }> => {
        const radius = markerRadius(image!.naturalWidth, image!.naturalHeight);
        return {
            kind: "marker",
            x: Math.max(radius, Math.min(image!.naturalWidth - radius, x)),
            y: Math.max(radius, Math.min(image!.naturalHeight - radius, y)),
            number,
            color,
            radius,
        };
    };

    const updateDraft = (shift: boolean) => {
        const draft = draftRef.current;
        const raw = rawRegionRef.current;
        if (!draft || !raw || draft.kind === "pen" || draft.kind === "marker")
            return;
        const region =
            shift &&
            (draft.kind === "line" ||
                draft.kind === "arrow" ||
                draft.kind === "rect")
                ? constrainRegion(raw, draft.kind, {
                      width: image!.naturalWidth,
                      height: image!.naturalHeight,
                  })
                : raw;
        Object.assign(draft, region);
        paint();
    };

    const onPointerDown = (ev: React.PointerEvent<HTMLCanvasElement>) => {
        if (ev.button !== 0 || saving || !image) return;
        setSelectionError(null);
        ev.preventDefault();
        ev.currentTarget.focus({ preventScroll: true });
        const { x, y } = toImageCoords(ev);
        if (pickingColor) {
            sampleColor(x, y);
            return;
        }
        ev.currentTarget.setPointerCapture(ev.pointerId);
        if (tool === "marker") {
            draftRef.current = makeMarker(x, y, nextMarkerNumber(ops));
            paint();
            return;
        }
        rawRegionRef.current = { x0: x, y0: y, x1: x, y1: y };
        if (tool === "pen") {
            draftRef.current = {
                kind: "pen",
                color,
                width: strokeWidth,
                points: [[x, y]],
            };
        } else if (tool === "rect" || tool === "arrow" || tool === "line") {
            draftRef.current = {
                kind: tool,
                color,
                width: strokeWidth,
                ...rawRegionRef.current,
            };
        } else if (tool === "pixelate") {
            draftRef.current = {
                kind: tool,
                blendWithBorder,
                ...rawRegionRef.current,
            };
        } else {
            draftRef.current = { kind: tool, ...rawRegionRef.current };
        }
        paint();
    };

    const onPointerMove = (ev: React.PointerEvent<HTMLCanvasElement>) => {
        const draft = draftRef.current;
        if (!draft || saving) return;
        const { x, y } = toImageCoords(ev);
        if (draft.kind === "pen") {
            draft.points.push([x, y]);
            paint();
        } else if (draft.kind === "marker") {
            draftRef.current = makeMarker(x, y, draft.number);
            paint();
        } else if (rawRegionRef.current) {
            rawRegionRef.current.x1 = x;
            rawRegionRef.current.y1 = y;
            updateDraft(ev.shiftKey);
        }
    };

    const cancelDraft = () => {
        draftRef.current = null;
        rawRegionRef.current = null;
        paint();
    };

    const onPointerUp = (ev: React.PointerEvent<HTMLCanvasElement>) => {
        let draft = draftRef.current;
        if (!draft || saving) return;
        if (draft.kind === "marker") {
            const { x, y } = toImageCoords(ev);
            draft = makeMarker(x, y, draft.number);
        }
        if (
            draft.kind !== "pen" &&
            draft.kind !== "marker" &&
            rawRegionRef.current
        ) {
            const { x, y } = toImageCoords(ev);
            rawRegionRef.current.x1 = x;
            rawRegionRef.current.y1 = y;
            updateDraft(ev.shiftKey);
        }
        draftRef.current = null;
        rawRegionRef.current = null;
        const isEmpty =
            draft.kind === "pen"
                ? draft.points.length < 2
                : draft.kind === "marker"
                  ? false
                  : draft.kind === "arrow" || draft.kind === "line"
                    ? Math.hypot(draft.x1 - draft.x0, draft.y1 - draft.y0) < 1
                    : Math.abs(draft.x1 - draft.x0) < 1 ||
                      Math.abs(draft.y1 - draft.y0) < 1;
        if (isEmpty) {
            if (
                draft.kind !== "pen" &&
                draft.kind !== "arrow" &&
                draft.kind !== "line" &&
                draft.kind !== "marker"
            ) {
                setSelectionError(
                    "Choose an area at least one pixel wide and high."
                );
            }
            paint();
            return;
        }
        const committed =
            draft.kind === "pixelate" && committedRef.current
                ? freezePixelate(draft, committedRef.current, activeCrop(ops))
                : draft;
        setOps((previous) => [
            ...previous,
            committed.kind === "marker"
                ? { ...committed, number: nextMarkerNumber(previous) }
                : committed,
        ]);
        setRedoStack([]);
    };

    const undo = () => {
        if (saving || ops.length === 0) return;
        setRedoStack([...redoStack, ops[ops.length - 1]]);
        setOps(ops.slice(0, -1));
    };

    const redo = () => {
        if (saving || redoStack.length === 0) return;
        setOps([...ops, redoStack[redoStack.length - 1]]);
        setRedoStack(redoStack.slice(0, -1));
    };

    const onKeyDown = (ev: React.KeyboardEvent) => {
        // Keep keystrokes from reaching a parent modal or the editor
        ev.stopPropagation();
        const target = ev.target as HTMLElement;
        const editingInput = target.matches("input, select, textarea");
        if (ev.key === "Shift" && !saving) updateDraft(true);
        if (ev.key === "Escape") {
            ev.preventDefault();
            if (pickingColor) {
                setPickingColor(false);
                setSelectionError(null);
                return;
            }
            if (draftRef.current) {
                cancelDraft();
                return;
            }
            if (!saving) props.onCancel();
            return;
        }
        if (!(ev.ctrlKey || ev.metaKey)) return;
        if (editingInput) return;
        const key = ev.key.toLowerCase();
        if (key === "z" && !ev.shiftKey) {
            ev.preventDefault();
            undo();
        } else if ((key === "z" && ev.shiftKey) || key === "y") {
            ev.preventDefault();
            redo();
        }
    };

    const onKeyUp = (event: React.KeyboardEvent) => {
        if (event.key === "Shift" && !saving) updateDraft(false);
    };

    const applyCustomColor = () => {
        if (/^#[0-9a-f]{6}$/i.test(colorText)) {
            setColor(colorText.toLowerCase());
            setPickingColor(false);
            setSelectionError(null);
        } else {
            setSelectionError("Enter a hex color such as #0070c0.");
            setColorText(color);
        }
    };

    const save = async () => {
        const committed = committedRef.current;
        if (!image || !committed || saving || ops.length === 0) return;
        setSaving(true);
        setSaveError(null);
        try {
            // The committed layer already contains the exact image and edits,
            // without the preview's selection outline or crop dimming. Export
            // that layer directly; only a crop needs a separate, smaller copy.
            const crop = activeCrop(ops);
            const output = crop ? cropCanvas(committed, crop) : committed;
            let blob: Blob;
            try {
                blob = await new Promise<Blob>((resolve, reject) =>
                    output.toBlob(
                        (b) =>
                            b ? resolve(b) : reject(new Error("Export failed")),
                        "image/png"
                    )
                );
            } finally {
                if (output !== committed) releaseCanvas(output);
            }
            await props.onSave(blob);
        } catch (err) {
            console.error(err);
            setSaveError(
                err instanceof Error && err.message
                    ? err.message
                    : "Could not save the image."
            );
            setSaving(false);
        }
    };

    const selectedGroup = TOOLS.find((t) => t.tool === tool)?.group;
    const selectedIsCensor = selectedGroup === "censor";

    const crop = activeCrop(ops);
    const outputSize = !image
        ? null
        : crop
          ? {
                width: Math.round(Math.abs(crop.x1 - crop.x0)),
                height: Math.round(Math.abs(crop.y1 - crop.y0)),
            }
          : { width: image.naturalWidth, height: image.naturalHeight };

    return (
        <ReactModal
            isOpen
            onRequestClose={() => !saving && props.onCancel()}
            contentLabel={props.title ?? "Edit image"}
            className="modal-dialog modal-dialog-centered gw-evidence-dialog gw-image-annotator-dialog"
            shouldCloseOnOverlayClick={false}
        >
            <div
                className="modal-content gw-evidence-dialog-content"
                onKeyDown={onKeyDown}
                onKeyUp={onKeyUp}
            >
                <div className="modal-header gw-evidence-dialog-header">
                    <div>
                        <span className="gw-evidence-dialog-eyebrow">
                            Report evidence
                        </span>
                        <h5 className="modal-title">
                            {props.title ?? "Edit image"}
                        </h5>
                    </div>
                    <button
                        type="button"
                        className="gw-evidence-dialog-close"
                        aria-label="Close"
                        disabled={saving}
                        onClick={props.onCancel}
                    >
                        <i className="fas fa-times" aria-hidden="true" />
                    </button>
                </div>

                <div className="gw-image-annotator-toolbar" role="toolbar">
                    {(["censor", "highlight", "adjust"] as const).map(
                        (group) => (
                            <div
                                key={group}
                                className="gw-image-annotator-group"
                                role="group"
                                aria-label={GROUP_LABELS[group]}
                            >
                                <span className="gw-image-annotator-group-label">
                                    {GROUP_LABELS[group]}
                                </span>
                                {TOOLS.filter((t) => t.group === group).map(
                                    (t) => (
                                        <button
                                            key={t.tool}
                                            type="button"
                                            title={t.label}
                                            aria-label={t.label}
                                            aria-pressed={tool === t.tool}
                                            disabled={saving}
                                            className={
                                                tool === t.tool
                                                    ? "is-active"
                                                    : undefined
                                            }
                                            onClick={() => {
                                                setTool(t.tool);
                                                setPickingColor(false);
                                                setSelectionError(null);
                                            }}
                                        >
                                            {t.tool === "marker" ? (
                                                <span
                                                    className="gw-image-annotator-number-icon"
                                                    aria-hidden="true"
                                                >
                                                    1
                                                </span>
                                            ) : (
                                                <FontAwesomeIcon
                                                    icon={t.icon}
                                                />
                                            )}
                                        </button>
                                    )
                                )}
                            </div>
                        )
                    )}
                    {tool === "pixelate" && (
                        <select
                            className="form-select form-select-sm w-auto"
                            aria-label="Pixelate colors"
                            title="Colors for new Pixelate selections"
                            disabled={saving}
                            value={blendWithBorder ? "border" : "neutral"}
                            onChange={(event) =>
                                setBlendWithBorder(
                                    event.target.value === "border"
                                )
                            }
                        >
                            <option value="border">Blend with border</option>
                            <option value="neutral">Neutral</option>
                        </select>
                    )}
                    <div
                        className="gw-image-annotator-group gw-image-annotator-colors"
                        role="group"
                        aria-label="Highlight color"
                    >
                        {COLORS.map((c) => (
                            <button
                                key={c}
                                type="button"
                                title={"Color " + c}
                                aria-label={"Color " + c}
                                aria-pressed={color === c}
                                disabled={
                                    saving || selectedGroup !== "highlight"
                                }
                                className={
                                    "gw-image-annotator-swatch" +
                                    (color === c ? " is-active" : "")
                                }
                                style={{ backgroundColor: c }}
                                onClick={() => {
                                    setColor(c);
                                    setPickingColor(false);
                                    setSelectionError(null);
                                }}
                            />
                        ))}
                        <input
                            type="color"
                            className="gw-image-annotator-color-input"
                            aria-label="Custom annotation color"
                            title="Custom annotation color"
                            value={color}
                            disabled={saving || selectedGroup !== "highlight"}
                            onChange={(event) => {
                                setColor(event.target.value);
                                setPickingColor(false);
                                setSelectionError(null);
                            }}
                        />
                        <input
                            type="text"
                            className="form-control form-control-sm gw-image-annotator-color-hex"
                            aria-label="Annotation color hex"
                            spellCheck={false}
                            autoComplete="off"
                            value={colorText}
                            disabled={saving || selectedGroup !== "highlight"}
                            onChange={(event) =>
                                setColorText(event.target.value)
                            }
                            onBlur={applyCustomColor}
                            onKeyDown={(event) => {
                                if (event.key === "Enter") {
                                    event.preventDefault();
                                    applyCustomColor();
                                }
                            }}
                        />
                        <button
                            type="button"
                            aria-label="Pick color from image"
                            title="Pick color from image"
                            aria-pressed={pickingColor}
                            disabled={
                                !image ||
                                saving ||
                                selectedGroup !== "highlight"
                            }
                            className={pickingColor ? "is-active" : undefined}
                            onClick={() => {
                                setPickingColor(!pickingColor);
                                setSelectionError(null);
                            }}
                        >
                            <FontAwesomeIcon icon={faEyeDropper} />
                        </button>
                    </div>
                    <div className="gw-image-annotator-group" role="group">
                        <button
                            type="button"
                            title="Undo (Ctrl+Z)"
                            aria-label="Undo"
                            disabled={saving || ops.length === 0}
                            onClick={undo}
                        >
                            <FontAwesomeIcon icon={faRotateLeft} />
                        </button>
                        <button
                            type="button"
                            title="Redo (Ctrl+Shift+Z)"
                            aria-label="Redo"
                            disabled={saving || redoStack.length === 0}
                            onClick={redo}
                        >
                            <FontAwesomeIcon icon={faRotateRight} />
                        </button>
                        <button
                            type="button"
                            title="Remove all edits"
                            aria-label="Remove all edits"
                            disabled={saving || ops.length === 0}
                            onClick={() => {
                                setRedoStack([]);
                                setOps([]);
                            }}
                        >
                            <FontAwesomeIcon icon={faTrashCan} />
                        </button>
                    </div>
                </div>

                <div className="modal-body gw-image-annotator-body">
                    {loadError ? (
                        <div className="alert alert-danger" role="alert">
                            The image could not be loaded.
                        </div>
                    ) : !image ? (
                        <div className="gw-image-annotator-loading">
                            <i
                                className="fas fa-spinner fa-spin"
                                aria-hidden="true"
                            />{" "}
                            Loading image…
                        </div>
                    ) : null}
                    {selectionError && (
                        <div className="alert alert-danger" role="alert">
                            {selectionError}
                        </div>
                    )}
                    <canvas
                        ref={setCanvas}
                        hidden={!image}
                        className={
                            "gw-image-annotator-canvas" +
                            (pickingColor ? " is-picking-color" : "")
                        }
                        tabIndex={0}
                        aria-label="Image annotation canvas"
                        onPointerDown={onPointerDown}
                        onPointerMove={onPointerMove}
                        onPointerUp={onPointerUp}
                        onPointerCancel={cancelDraft}
                    />
                </div>

                <div className="modal-footer gw-evidence-dialog-footer gw-image-annotator-footer">
                    <p className="gw-image-annotator-hint" aria-live="polite">
                        {pickingColor ? (
                            "Click a visible image pixel to sample its color. Escape cancels the pipette."
                        ) : tool === "marker" ? (
                            `Click to place marker ${nextMarkerNumber(ops)}. The next marker increments automatically.`
                        ) : tool === "line" ||
                          tool === "arrow" ||
                          tool === "rect" ? (
                            "Hold Shift for horizontal, vertical, or 45° lines/arrows, or square rectangles."
                        ) : tool === "crop" ? (
                            <>
                                Drag to choose the area to keep. Drag again to
                                change it, or undo to remove it.
                                {outputSize && (
                                    <>
                                        {" "}
                                        <strong>
                                            {outputSize.width} ×{" "}
                                            {outputSize.height} px
                                        </strong>
                                    </>
                                )}
                            </>
                        ) : selectedIsCensor && tool !== "blackout" ? (
                            <>
                                Pixelate replaces the selection with an opaque,
                                generated mosaic. Choose border blending or
                                neutral colors before drawing. Cover the entire
                                secret, including its edges, before saving.
                            </>
                        ) : (
                            "Drag over the image to select an area."
                        )}
                    </p>
                    {props.notice && (
                        <p className="gw-image-annotator-notice" role="note">
                            {props.notice}
                        </p>
                    )}
                    {saveError && (
                        <div
                            className="alert alert-danger gw-evidence-upload-alert"
                            role="alert"
                        >
                            {saveError}
                        </div>
                    )}
                    <div className="gw-evidence-dialog-primary-actions">
                        <button
                            type="button"
                            className="btn btn-outline-secondary"
                            disabled={saving}
                            onClick={props.onCancel}
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            className="btn gw-evidence-primary-action"
                            disabled={!image || saving || ops.length === 0}
                            onClick={save}
                        >
                            {saving ? (
                                <>
                                    <i
                                        className="fas fa-spinner fa-spin"
                                        aria-hidden="true"
                                    />
                                    Saving…
                                </>
                            ) : (
                                <>
                                    <i
                                        className="fas fa-check"
                                        aria-hidden="true"
                                    />
                                    {props.saveLabel ?? "Save image"}
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </ReactModal>
    );
}
