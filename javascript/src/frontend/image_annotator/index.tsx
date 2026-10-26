import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faSquare as faSquareOutline } from "@fortawesome/free-regular-svg-icons/faSquare";
import { faArrowRightLong } from "@fortawesome/free-solid-svg-icons/faArrowRightLong";
import { faCropSimple } from "@fortawesome/free-solid-svg-icons/faCropSimple";
import { faDroplet } from "@fortawesome/free-solid-svg-icons/faDroplet";
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
    defaultStrokeWidth,
    drawCropOverlay,
    drawOp,
    renderImage,
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
    { tool: "blur", label: "Blur", icon: faDroplet, group: "censor" },
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
    { tool: "pen", label: "Pen", icon: faPen, group: "highlight" },
    { tool: "crop", label: "Crop", icon: faCropSimple, group: "adjust" },
];

const COLORS = ["#e00000", "#ff9500", "#ffd400", "#00b050", "#0070c0"];

/**
 * Modal for censoring (black box, pixelate, blur), highlighting (rectangle, arrow, pen),
 * and cropping an image before it's used as report evidence.
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
    // Render of the image and committed ops, reused while an op is being drawn
    const committedRef = useRef<HTMLCanvasElement | null>(null);
    const draftRef = useRef<AnnotationOp | null>(null);

    const [image, setImage] = useState<HTMLImageElement | null>(null);
    const [loadError, setLoadError] = useState(false);
    const [ops, setOps] = useState<AnnotationOp[]>([]);
    const [redoStack, setRedoStack] = useState<AnnotationOp[]>([]);
    const [tool, setTool] = useState<Tool>("blackout");
    const [color, setColor] = useState(COLORS[0]);
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState<string | null>(null);

    useEffect(() => {
        let objectUrl: string | null = null;
        const src =
            typeof props.source === "string"
                ? props.source
                : (objectUrl = URL.createObjectURL(props.source));
        const img = new Image();
        img.onload = () => setImage(img);
        img.onerror = () => setLoadError(true);
        img.src = src;
        return () => {
            img.onload = img.onerror = null;
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        };
    }, [props.source]);

    const strokeWidth = image
        ? defaultStrokeWidth(image.naturalWidth, image.naturalHeight)
        : 3;

    const paint = useCallback(() => {
        const canvas = canvasRef.current;
        const committed = committedRef.current;
        if (!canvas || !committed) return;
        const ctx = canvas.getContext("2d")!;
        ctx.drawImage(committed, 0, 0);
        const draft = draftRef.current;
        if (draft && draft.kind !== "crop") {
            drawOp(ctx, draft);
            if (
                draft.kind === "blackout" ||
                draft.kind === "blur" ||
                draft.kind === "pixelate"
            ) {
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
        canvasRef.current.width = image.naturalWidth;
        canvasRef.current.height = image.naturalHeight;
        committedRef.current = renderImage(image, ops);
        paint();
    }, [image, ops, paint]);

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

    const onPointerDown = (ev: React.PointerEvent<HTMLCanvasElement>) => {
        if (ev.button !== 0 || saving) return;
        ev.preventDefault();
        ev.currentTarget.setPointerCapture(ev.pointerId);
        const { x, y } = toImageCoords(ev);
        if (tool === "pen") {
            draftRef.current = {
                kind: "pen",
                color,
                width: strokeWidth,
                points: [[x, y]],
            };
        } else if (tool === "rect" || tool === "arrow") {
            draftRef.current = {
                kind: tool,
                color,
                width: strokeWidth,
                x0: x,
                y0: y,
                x1: x,
                y1: y,
            };
        } else {
            draftRef.current = { kind: tool, x0: x, y0: y, x1: x, y1: y };
        }
        paint();
    };

    const onPointerMove = (ev: React.PointerEvent<HTMLCanvasElement>) => {
        const draft = draftRef.current;
        if (!draft) return;
        const { x, y } = toImageCoords(ev);
        if (draft.kind === "pen") {
            draft.points.push([x, y]);
        } else {
            draft.x1 = x;
            draft.y1 = y;
        }
        paint();
    };

    const onPointerUp = () => {
        const draft = draftRef.current;
        draftRef.current = null;
        if (!draft) return;
        const isEmpty =
            draft.kind === "pen"
                ? draft.points.length < 2
                : Math.abs(draft.x1 - draft.x0) < 2 &&
                  Math.abs(draft.y1 - draft.y0) < 2;
        if (isEmpty) {
            paint();
            return;
        }
        setOps((prev) => [...prev, draft]);
        setRedoStack([]);
    };

    const undo = () => {
        if (ops.length === 0) return;
        setRedoStack([...redoStack, ops[ops.length - 1]]);
        setOps(ops.slice(0, -1));
    };

    const redo = () => {
        if (redoStack.length === 0) return;
        setOps([...ops, redoStack[redoStack.length - 1]]);
        setRedoStack(redoStack.slice(0, -1));
    };

    const onKeyDown = (ev: React.KeyboardEvent) => {
        // Keep keystrokes from reaching a parent modal or the editor
        ev.stopPropagation();
        if (ev.key === "Escape") {
            ev.preventDefault();
            if (!saving) props.onCancel();
            return;
        }
        if (!(ev.ctrlKey || ev.metaKey)) return;
        const key = ev.key.toLowerCase();
        if (key === "z" && !ev.shiftKey) {
            ev.preventDefault();
            undo();
        } else if ((key === "z" && ev.shiftKey) || key === "y") {
            ev.preventDefault();
            redo();
        }
    };

    const save = async () => {
        if (!image) return;
        setSaving(true);
        setSaveError(null);
        try {
            const output = renderImage(image, ops, true);
            const blob = await new Promise<Blob>((resolve, reject) =>
                output.toBlob(
                    (b) =>
                        b ? resolve(b) : reject(new Error("Export failed")),
                    "image/png"
                )
            );
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
                                            className={
                                                tool === t.tool
                                                    ? "is-active"
                                                    : undefined
                                            }
                                            onClick={() => setTool(t.tool)}
                                        >
                                            <FontAwesomeIcon icon={t.icon} />
                                        </button>
                                    )
                                )}
                            </div>
                        )
                    )}
                    <div
                        className="gw-image-annotator-group"
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
                                disabled={selectedGroup !== "highlight"}
                                className={
                                    "gw-image-annotator-swatch" +
                                    (color === c ? " is-active" : "")
                                }
                                style={{ backgroundColor: c }}
                                onClick={() => setColor(c)}
                            />
                        ))}
                    </div>
                    <div className="gw-image-annotator-group" role="group">
                        <button
                            type="button"
                            title="Undo (Ctrl+Z)"
                            aria-label="Undo"
                            disabled={ops.length === 0}
                            onClick={undo}
                        >
                            <FontAwesomeIcon icon={faRotateLeft} />
                        </button>
                        <button
                            type="button"
                            title="Redo (Ctrl+Shift+Z)"
                            aria-label="Redo"
                            disabled={redoStack.length === 0}
                            onClick={redo}
                        >
                            <FontAwesomeIcon icon={faRotateRight} />
                        </button>
                        <button
                            type="button"
                            title="Remove all edits"
                            aria-label="Remove all edits"
                            disabled={ops.length === 0}
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
                    <canvas
                        ref={canvasRef}
                        hidden={!image}
                        className="gw-image-annotator-canvas"
                        onPointerDown={onPointerDown}
                        onPointerMove={onPointerMove}
                        onPointerUp={onPointerUp}
                        onPointerCancel={onPointerUp}
                    />
                </div>

                <div className="modal-footer gw-evidence-dialog-footer gw-image-annotator-footer">
                    <p className="gw-image-annotator-hint">
                        {tool === "crop" ? (
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
                                <strong>Tip:</strong> blurred or pixelated text
                                can sometimes be reconstructed. Use{" "}
                                <em>Black box</em> for passwords, hashes, and
                                other secrets.
                            </>
                        ) : (
                            props.notice
                        )}
                    </p>
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
