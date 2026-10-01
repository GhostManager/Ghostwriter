import { useId, useMemo, useState } from "react";
import ReactModal from "react-modal";
import { Editor } from "@tiptap/core";
import { getCsrfToken } from "../../../services/csrf";

type OplogChoice = {
    id: number;
    name: string;
};

type OutlineBlock =
    | {
          type: "narrative";
          timestamp: string;
          tool: string;
          command: string;
          user_context: string;
          dest: string;
          has_comments: boolean;
      }
    | { type: "paragraph"; text: string }
    | { type: "html"; html: string }
    | { type: "code"; text: string }
    | { type: "reference"; ref: string }
    | { type: "evidence"; evidence_id: number };

type ToastLevel = "success" | "warning" | "error" | "info";

declare global {
    interface Window {
        displayToastTop?: (args: {
            type: ToastLevel;
            string: string;
            title?: string;
            delay?: number;
        }) => void;
    }
}

function showToast(type: ToastLevel, string: string, title = "Oplog Outline") {
    window.displayToastTop?.({ type, string, title });
}

function getOplogChoices(): OplogChoice[] {
    const el = document.getElementById("report-oplog-options");
    if (!el?.textContent) {
        return [];
    }
    return JSON.parse(el.textContent) as OplogChoice[];
}

function getGenerateUrl(): string {
    return (
        document.getElementById("report-oplog-outline-url")?.textContent ?? ""
    );
}

function buildNarrativeContent(
    block: Extract<OutlineBlock, { type: "narrative" }>
) {
    const content: Array<{
        type: "text";
        text: string;
        marks?: Array<{ type: string }>;
    }> = [
        {
            type: "text",
            text: `${block.timestamp}, the assessment team used ${block.tool}`,
        },
    ];

    if (block.command) {
        content.push(
            { type: "text", text: " (" },
            { type: "text", text: block.command, marks: [{ type: "code" }] },
            { type: "text", text: ")" }
        );
    }

    content.push(
        { type: "text", text: " as " },
        {
            type: "text",
            text: block.user_context,
            marks: [{ type: "italic" }],
        },
        {
            type: "text",
            text: ` against ${block.dest}.${block.has_comments ? " Comments:" : ""}`,
        }
    );

    return content;
}

function literalBlock(content: Record<string, unknown>) {
    return {
        type: "jinjaLiteral",
        content: [content],
    };
}

function literalHtmlBlock(html: string) {
    const wrapper = document.createElement("div");
    wrapper.setAttribute("data-gw-jinja-literal", "true");
    wrapper.innerHTML = html;
    return wrapper.outerHTML;
}

export default function OplogOutlineButton({ editor }: { editor: Editor }) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            <button
                type="button"
                tabIndex={-1}
                title="Append oplog outline"
                onClick={(ev) => {
                    ev.preventDefault();
                    setIsOpen(true);
                }}
            >
                Insert Log Narrative
            </button>
            {isOpen && (
                <OplogOutlineModal
                    editor={editor}
                    onClose={() => setIsOpen(false)}
                />
            )}
        </>
    );
}

function OplogOutlineModal(props: { editor: Editor; onClose: () => void }) {
    const oplogs = useMemo(() => getOplogChoices(), []);
    const [selectedId, setSelectedId] = useState<number | null>(
        oplogs.length === 1 ? oplogs[0].id : null
    );
    const [state, setState] = useState<"idle" | "loading">("idle");
    const selectId = useId();

    const disabled = state === "loading";
    const canSubmit = selectedId !== null && !disabled;

    return (
        <ReactModal
            isOpen
            onRequestClose={props.onClose}
            contentLabel="Append Oplog Outline"
            className="modal-dialog modal-dialog-centered gw-editor-dialog gw-editor-dialog-wide"
        >
            <div className="modal-content gw-editor-dialog-content">
                <div className="modal-header gw-editor-dialog-header">
                    <div>
                        <span className="gw-editor-dialog-eyebrow">
                            Narrative builder
                        </span>
                        <h5 className="modal-title">Append oplog outline</h5>
                        <p className="gw-editor-dialog-intro">
                            Turn reportable operation log activity into an
                            editable narrative outline.
                        </p>
                    </div>
                    <button
                        type="button"
                        className="gw-editor-dialog-close"
                        aria-label="Close oplog outline dialog"
                        disabled={disabled}
                        onClick={props.onClose}
                    >
                        <i className="fas fa-times" aria-hidden="true" />
                    </button>
                </div>
                <form
                    className="gw-editor-dialog-form"
                    onSubmit={(ev) => {
                        ev.preventDefault();
                        void appendOutline(
                            props.editor,
                            selectedId,
                            setState,
                            props.onClose
                        );
                    }}
                >
                    <div className="modal-body gw-editor-dialog-body">
                        <div className="gw-editor-dialog-note">
                            <i className="fas fa-stream" aria-hidden="true" />
                            <p>
                                Entries tagged <code>report</code> or{" "}
                                <code>evidence</code> are appended to the end of
                                this field. Linked evidence is included, and the
                                generated outline remains fully editable.
                            </p>
                        </div>
                        <div className="gw-editor-dialog-field">
                            <label htmlFor={selectId}>Operation log</label>
                            <select
                                id={selectId}
                                className="custom-select"
                                disabled={disabled || oplogs.length === 0}
                                value={selectedId?.toString() ?? ""}
                                onChange={(ev) => {
                                    setSelectedId(
                                        ev.target.value === ""
                                            ? null
                                            : parseInt(ev.target.value, 10)
                                    );
                                }}
                            >
                                <option value="">Select a log...</option>
                                {oplogs.map((oplog) => (
                                    <option key={oplog.id} value={oplog.id}>
                                        {oplog.name}
                                    </option>
                                ))}
                            </select>
                            <small className="form-text">
                                Choose the activity log to use for this
                                narrative.
                            </small>
                        </div>
                        {oplogs.length === 0 && (
                            <div
                                className="alert alert-warning gw-editor-dialog-alert"
                                role="alert"
                            >
                                No operation logs are available for this
                                report&apos;s project.
                            </div>
                        )}
                    </div>
                    <div className="modal-footer gw-editor-dialog-footer">
                        <button
                            type="button"
                            className="btn btn-outline-secondary"
                            disabled={disabled}
                            onClick={props.onClose}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="btn gw-editor-primary-action"
                            disabled={!canSubmit}
                        >
                            <i
                                className={
                                    disabled
                                        ? "fas fa-circle-notch fa-spin"
                                        : "fas fa-stream"
                                }
                                aria-hidden="true"
                            />
                            {disabled
                                ? "Building outline..."
                                : "Append outline"}
                        </button>
                    </div>
                </form>
            </div>
        </ReactModal>
    );
}

async function appendOutline(
    editor: Editor,
    oplogId: number | null,
    setState: (state: "idle" | "loading") => void,
    close: () => void
) {
    if (oplogId === null) {
        showToast("warning", "Select an oplog before generating the outline.");
        return;
    }

    const csrfToken = getCsrfToken();
    if (!csrfToken) {
        showToast("error", "CSRF token not found. Please refresh the page.");
        return;
    }

    const url = getGenerateUrl();
    if (!url) {
        showToast("error", "Outline generation URL is missing.");
        return;
    }

    setState("loading");
    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({ oplog_id: oplogId }),
        });
        const payload = (await response.json()) as {
            blocks?: OutlineBlock[];
            message?: string;
        };

        if (!response.ok) {
            showToast(
                "error",
                payload.message || "Could not generate the oplog outline."
            );
            return;
        }

        const blocks = payload.blocks ?? [];
        if (blocks.length === 0) {
            showToast(
                "info",
                "No reportable oplog entries were found for this log."
            );
            close();
            return;
        }

        blocks.forEach((block) => {
            if (block.type === "narrative") {
                editor
                    .chain()
                    .focus("end")
                    .insertContent(
                        literalBlock({
                            type: "paragraph",
                            content: buildNarrativeContent(block),
                        })
                    )
                    .run();
            } else if (block.type === "paragraph") {
                editor
                    .chain()
                    .focus("end")
                    .insertContent(
                        literalBlock({
                            type: "paragraph",
                            content: block.text
                                ? [{ type: "text", text: block.text }]
                                : [],
                        })
                    )
                    .run();
            } else if (block.type === "html") {
                editor
                    .chain()
                    .focus("end")
                    .insertContent(literalHtmlBlock(block.html))
                    .run();
            } else if (block.type === "code") {
                editor
                    .chain()
                    .focus("end")
                    .insertContent(
                        literalBlock({
                            type: "codeBlock",
                            content: block.text
                                ? [{ type: "text", text: block.text }]
                                : [],
                        })
                    )
                    .run();
            } else if (block.type === "reference") {
                editor
                    .chain()
                    .focus("end")
                    .insertContent(
                        literalBlock({
                            type: "paragraph",
                            content: [
                                {
                                    type: "jinjaReference",
                                    attrs: { ref: block.ref },
                                },
                            ],
                        })
                    )
                    .run();
            } else {
                editor
                    .chain()
                    .focus("end")
                    .insertContent({
                        type: "evidence",
                        attrs: { id: block.evidence_id },
                    })
                    .run();
            }
        });
        close();
    } catch (error) {
        console.error(error);
        showToast("error", "Could not generate the oplog outline.");
    } finally {
        setState("idle");
    }
}
