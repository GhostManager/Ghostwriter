import { mergeAttributes, Node, NodeViewProps } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import React, { useContext, useEffect, useRef, useState } from "react";
import ReactModal from "react-modal";
import ImageAnnotator from "../frontend/image_annotator";

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        evidence: {
            setEvidence: (options: { id: number }) => ReturnType;
        };
    }
}

type EvidenceOptions = {};
const Evidence = Node.create<EvidenceOptions>({
    name: "evidence",
    group: "block",
    draggable: true,

    addAttributes() {
        return {
            id: {
                default: null,
                parseHTML: (el) => el.getAttribute("data-evidence-id"),
                renderHTML: (attrs) => ({
                    "data-evidence-id": attrs.id,
                }),
            },
        };
    },

    parseHTML() {
        return [
            {
                tag: "div",
                getAttrs: (node) =>
                    node.classList.contains("richtext-evidence") && null,
            },
        ];
    },

    renderText({ node }) {
        return node.attrs.name ? "Evidence " + node.attrs.name : "Evidence";
    },

    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(
                {
                    class: "richtext-evidence",
                },
                HTMLAttributes
            ),
        ];
    },

    addNodeView() {
        return ReactNodeViewRenderer(EvidenceView);
    },

    addCommands() {
        return {
            setEvidence:
                (options) =>
                ({ commands }) =>
                    commands.insertContent({
                        type: this.name,
                        attrs: options,
                    }),
        };
    },

    addKeyboardShortcuts() {
        return {
            "Mod-Shift-d": () =>
                this.editor.view.dom.dispatchEvent(
                    new CustomEvent("openevidencemodal")
                ),
        };
    },
});

export type ReportWidthUnit = "" | "percent" | "px";

export type Evidence = {
    id: number;
    friendlyName: string;
    caption: string;
    document: string;
    reportWidthUnit?: string;
    reportWidthValue?: number | null;
};

export type Evidences = {
    evidence: Evidence[];
    uploadUrl: string;
    poll: () => Promise<void>;
    /** Change an evidence's report caption. Rejects with a user-facing message on failure. */
    updateCaption?: (id: number, caption: string) => Promise<void>;
    /** Replace an image evidence's file with an edited copy. Rejects with a user-facing message on failure. */
    replaceImage?: (id: number, image: Blob) => Promise<void>;
    /** Change how large an image evidence is in the report. Rejects with a user-facing message on failure. */
    updateReportSize?: (
        id: number,
        unit: ReportWidthUnit,
        value: number | null
    ) => Promise<void>;
};

export const EvidencesContext = React.createContext<Evidences | null>(null);

const TEXT_EXTENSIONS = [".txt", ".log", ".md"];
const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg"];

// Custom hook to fetch text content of an evidence if it's a text file
function useTextContent(id: number, isText: boolean): string | null {
    const [content, setContent] = React.useState<string | null>(null);
    React.useEffect(() => {
        if (!isText) return;
        fetch("/reporting/evidence/download/" + id)
            .then((r) => {
                if (!r.ok) throw new Error(r.statusText);
                return r.text();
            })
            .then(setContent)
            .catch(() => setContent(null));
    }, [id, isText]);
    return content;
}

function EvidenceView(props: NodeViewProps) {
    const id = parseInt(props.node.attrs.id);
    const ghostwriterEvidences = useContext(EvidencesContext);
    const evidence =
        ghostwriterEvidences &&
        ghostwriterEvidences.evidence.find((v) => v.id === id);
    const normalizedDocument = evidence?.document.toLowerCase() ?? "";

    const [lightboxOpen, setLightboxOpen] = useState(false);
    const [annotatorOpen, setAnnotatorOpen] = useState(false);

    const isImage =
        !!evidence &&
        IMAGE_EXTENSIONS.some((ext) => normalizedDocument.endsWith(ext));
    const isText =
        !!evidence &&
        TEXT_EXTENSIONS.some((ext) => normalizedDocument.endsWith(ext));
    const textContent = useTextContent(id, isText);

    if (!evidence) {
        return (
            <NodeViewWrapper className="richtext-evidence">
                <span className="richtext-evidence-missing">
                    « Evidence Missing »
                </span>
            </NodeViewWrapper>
        );
    }

    const editable = props.editor.isEditable;
    const replaceImage = ghostwriterEvidences?.replaceImage;
    const updateCaption = ghostwriterEvidences?.updateCaption;
    const updateReportSize = ghostwriterEvidences?.updateReportSize;
    const sizeUnit = normalizeUnit(evidence.reportWidthUnit);
    const sizeValue = evidence.reportWidthValue ?? null;

    let preview = null;
    if (isImage) {
        // The stored file name changes when the image is replaced, so use it to bust the cache
        const url =
            "/reporting/evidence/download/" +
            evidence.id +
            "?v=" +
            encodeURIComponent(evidence.document);
        preview = (
            <>
                <img
                    src={url}
                    style={{
                        width: `${PREVIEW_WIDTH_PX * previewScale(sizeUnit, sizeValue)}px`,
                    }}
                    onClick={() => setLightboxOpen(true)}
                />
                {editable && replaceImage && (
                    <button
                        type="button"
                        className="richtext-evidence-action"
                        title="Censor, highlight, or crop this image"
                        onClick={() => setAnnotatorOpen(true)}
                    >
                        <i className="fas fa-highlighter" aria-hidden="true" />{" "}
                        Edit image
                    </button>
                )}
                {editable && updateReportSize ? (
                    <ReportSizeEditor
                        unit={sizeUnit}
                        value={sizeValue}
                        onSave={(unit, value) =>
                            updateReportSize(evidence.id, unit, value)
                        }
                    />
                ) : (
                    sizeUnit && (
                        <span className="richtext-evidence-size">
                            {"Report size: " +
                                describeReportSize(sizeUnit, sizeValue)}
                        </span>
                    )
                )}
                <ReactModal
                    isOpen={lightboxOpen}
                    onRequestClose={() => setLightboxOpen(false)}
                    contentLabel="Lightbox"
                    className="rich-text-lightbox"
                >
                    <img src={url} />
                </ReactModal>
                {annotatorOpen && replaceImage && (
                    <ImageAnnotator
                        source={url}
                        title={"Edit " + evidence.friendlyName}
                        saveLabel="Replace evidence image"
                        notice={
                            <>
                                Saving replaces this evidence file everywhere it
                                is used, and the original is deleted.
                            </>
                        }
                        onCancel={() => setAnnotatorOpen(false)}
                        onSave={async (blob) => {
                            await replaceImage(evidence.id, blob);
                            setAnnotatorOpen(false);
                        }}
                    />
                )}
            </>
        );
    } else if (isText) {
        preview = (
            <pre className="richtext-evidence-text">
                <code>{textContent === null ? "Loading…" : textContent}</code>
            </pre>
        );
    }

    return (
        <NodeViewWrapper className="richtext-evidence">
            <span className="richtext-evidence-name">
                {evidence.friendlyName}
            </span>
            {preview}
            {editable && updateCaption ? (
                <CaptionEditor
                    caption={evidence.caption}
                    onSave={(caption) => updateCaption(evidence.id, caption)}
                />
            ) : (
                <span className="richtext-evidence-caption">
                    {"Evidence: " + evidence.caption}
                </span>
            )}
        </NodeViewWrapper>
    );
}

/** Width of the image thumbnail in the editor when it fills the report's evidence width. */
const PREVIEW_WIDTH_PX = 300;
/**
 * Pixels for the default 6.5" evidence width at 96 DPI. Templates can use another width,
 * so pixel sizes are only previewed approximately.
 */
const DEFAULT_REPORT_WIDTH_PX = 6.5 * 96;

function normalizeUnit(unit: string | undefined): ReportWidthUnit {
    return unit === "percent" || unit === "px" ? unit : "";
}

/** Fraction of the full evidence width the image will take in the report. */
function previewScale(unit: ReportWidthUnit, value: number | null): number {
    if (!unit || !value) return 1;
    const fraction =
        unit === "percent" ? value / 100 : value / DEFAULT_REPORT_WIDTH_PX;
    return Math.max(0.05, Math.min(1, fraction));
}

function describeReportSize(
    unit: ReportWidthUnit,
    value: number | null
): string {
    if (!unit || !value) return "full width";
    return unit === "percent" ? `${value}% width` : `${value} px wide`;
}

/** Click-to-edit control for how large an image appears in the generated report. */
function ReportSizeEditor(props: {
    unit: ReportWidthUnit;
    value: number | null;
    onSave: (unit: ReportWidthUnit, value: number | null) => Promise<void>;
}) {
    const [editing, setEditing] = useState(false);
    const [unit, setUnit] = useState<ReportWidthUnit>(props.unit);
    const [value, setValue] = useState(
        props.value === null ? "" : String(props.value)
    );
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Pick up changes made by collaborators or on the evidence page while not editing
    useEffect(() => {
        if (editing) return;
        setUnit(props.unit);
        setValue(props.value === null ? "" : String(props.value));
    }, [props.unit, props.value, editing]);

    const cancel = () => {
        setUnit(props.unit);
        setValue(props.value === null ? "" : String(props.value));
        setError(null);
        setEditing(false);
    };

    const commit = async () => {
        let parsed: number | null = null;
        if (unit) {
            parsed = Number(value);
            if (!Number.isInteger(parsed) || parsed < 1) {
                setError("Enter a whole number greater than zero.");
                return;
            }
            if (unit === "percent" && parsed > 100) {
                setError("Percentages must be between 1 and 100.");
                return;
            }
        }
        if (unit === props.unit && parsed === props.value) {
            cancel();
            return;
        }
        setSaving(true);
        setError(null);
        try {
            await props.onSave(unit, parsed);
            setEditing(false);
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Could not save the size."
            );
        } finally {
            setSaving(false);
        }
    };

    if (!editing) {
        return (
            <button
                type="button"
                className="richtext-evidence-size richtext-evidence-caption-button"
                title="Change how large this image is in the report"
                onClick={() => setEditing(true)}
            >
                {"Report size: " + describeReportSize(props.unit, props.value)}
                <i
                    className="fas fa-pencil-alt richtext-evidence-caption-icon"
                    aria-hidden="true"
                />
                <span className="visually-hidden"> (edit report size)</span>
            </button>
        );
    }

    return (
        <span
            className="richtext-evidence-caption-editor richtext-evidence-size-editor"
            onKeyDown={(e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    commit();
                } else if (e.key === "Escape") {
                    e.preventDefault();
                    cancel();
                }
            }}
        >
            <span className="richtext-evidence-caption-prefix">
                Report size:
            </span>
            <select
                className="form-select form-select-sm"
                aria-label="Report size unit"
                value={unit}
                disabled={saving}
                onChange={(e) => {
                    const next = normalizeUnit(e.target.value);
                    setUnit(next);
                    if (next === "percent" && !value) setValue("50");
                }}
            >
                <option value="">Full width</option>
                <option value="percent">Percent of width</option>
                <option value="px">Width in pixels</option>
            </select>
            {unit && (
                <input
                    type="number"
                    className={
                        "form-control form-control-sm" +
                        (error ? " is-invalid" : "")
                    }
                    aria-label={
                        unit === "percent"
                            ? "Percent of width"
                            : "Width in pixels"
                    }
                    min={1}
                    max={unit === "percent" ? 100 : undefined}
                    step={1}
                    value={value}
                    disabled={saving}
                    autoFocus
                    onChange={(e) => setValue(e.target.value)}
                />
            )}
            <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                disabled={saving}
                onClick={cancel}
            >
                Cancel
            </button>
            <button
                type="button"
                className="btn btn-sm gw-evidence-primary-action"
                disabled={saving}
                onClick={commit}
            >
                {saving ? (
                    <i className="fas fa-spinner fa-spin" aria-hidden="true" />
                ) : (
                    "Apply"
                )}
            </button>
            <span className="richtext-evidence-size-help">
                The aspect ratio is kept, and images are never enlarged.
            </span>
            {error && (
                <span className="richtext-evidence-caption-error" role="alert">
                    {error}
                </span>
            )}
        </span>
    );
}

const CAPTION_MAX_LENGTH = 255;

/** Click-to-edit caption shown under evidence in the editor. */
function CaptionEditor(props: {
    caption: string;
    onSave: (caption: string) => Promise<void>;
}) {
    const [editing, setEditing] = useState(false);
    const [value, setValue] = useState(props.caption);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement | null>(null);

    useEffect(() => {
        if (editing) inputRef.current?.select();
    }, [editing]);

    // Pick up changes made by collaborators or on the evidence page while not editing
    useEffect(() => {
        if (!editing) setValue(props.caption);
    }, [props.caption, editing]);

    const cancel = () => {
        setValue(props.caption);
        setError(null);
        setEditing(false);
    };

    const commit = async () => {
        const trimmed = value.trim();
        if (trimmed === props.caption) {
            cancel();
            return;
        }
        if (!trimmed) {
            setError("A caption is required.");
            return;
        }
        setSaving(true);
        setError(null);
        try {
            await props.onSave(trimmed);
            setEditing(false);
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Could not save caption."
            );
        } finally {
            setSaving(false);
        }
    };

    if (!editing) {
        return (
            <button
                type="button"
                className="richtext-evidence-caption richtext-evidence-caption-button"
                title="Edit caption"
                onClick={() => setEditing(true)}
            >
                {"Evidence: " + props.caption}
                <i
                    className="fas fa-pencil-alt richtext-evidence-caption-icon"
                    aria-hidden="true"
                />
                <span className="visually-hidden"> (edit caption)</span>
            </button>
        );
    }

    return (
        <span className="richtext-evidence-caption-editor">
            <span className="richtext-evidence-caption-prefix">Evidence:</span>
            <input
                ref={inputRef}
                type="text"
                className={"form-control" + (error ? " is-invalid" : "")}
                aria-label="Evidence caption"
                maxLength={CAPTION_MAX_LENGTH}
                value={value}
                disabled={saving}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => {
                    if (e.key === "Enter") {
                        e.preventDefault();
                        commit();
                    } else if (e.key === "Escape") {
                        e.preventDefault();
                        cancel();
                    }
                }}
                onBlur={() => {
                    if (!saving) commit();
                }}
            />
            {saving && (
                <i className="fas fa-spinner fa-spin" aria-hidden="true" />
            )}
            {error && (
                <span className="richtext-evidence-caption-error" role="alert">
                    {error}
                </span>
            )}
        </span>
    );
}

export default Evidence;
