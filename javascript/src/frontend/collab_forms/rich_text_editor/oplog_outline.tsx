import { useId, useMemo, useState } from "react";
import ReactModal from "react-modal";
import { Editor } from "@tiptap/core";
import { getCsrfToken } from "../../../services/csrf";

type OplogChoice = {
    id: number;
    name: string;
};

type OutlineBlock =
    | { type: "paragraph"; text: string }
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
    return document.getElementById("report-oplog-outline-url")?.textContent ?? "";
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
            className="modal-dialog modal-dialog-centered"
        >
            <div className="modal-content">
                <div className="modal-header">
                    <h5 className="modal-title">Append Oplog Outline</h5>
                </div>
                <div className="modal-body">
                    <p>
                        Appends a narrative outline based on operation log entries tagged with
                        <code> report </code>
                        or
                        <code> evidence </code>
                        to the end of this field. Any linked evidence will be included as well.
                    </p>
                    <p className="mb-3">
                        This is useful for quickly assembling a report
                        outline based on relevant activity recorded in the log(s).
                        You can edit the generated outline as needed after it has been inserted.
                    </p>
                    <div className="form-group">
                        <label htmlFor={selectId}>Operation Logs</label>
                        <select
                            id={selectId}
                            className="custom-select custom-select-lg"
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
                            <option value="">Select Log...</option>
                            {oplogs.map((oplog) => (
                                <option key={oplog.id} value={oplog.id}>
                                    {oplog.name}
                                </option>
                            ))}
                        </select>
                    </div>
                    {oplogs.length === 0 && (
                        <div className="alert alert-warning mb-0" role="alert">
                            No oplogs are available for this report&apos;s
                            project.
                        </div>
                    )}
                </div>
                <div className="modal-footer">
                    <button
                        className="btn btn-primary"
                        disabled={!canSubmit}
                        onClick={(ev) => {
                            ev.preventDefault();
                            void appendOutline(
                                props.editor,
                                selectedId,
                                setState,
                                props.onClose
                            );
                        }}
                    >
                        Append Outline
                    </button>
                    <button
                        className="btn btn-outline-secondary"
                        disabled={disabled}
                        onClick={(ev) => {
                            ev.preventDefault();
                            props.onClose();
                        }}
                    >
                        Cancel
                    </button>
                </div>
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

        editor
            .chain()
            .focus("end")
            .insertContent(
                blocks.map((block) =>
                    block.type === "paragraph"
                        ? {
                              type: "paragraph",
                              content: block.text
                                  ? [{ type: "text", text: block.text }]
                                  : [],
                          }
                        : {
                              type: "evidence",
                              attrs: { id: block.evidence_id },
                          }
                )
            )
            .run();
        close();
    } catch (error) {
        console.error(error);
        showToast("error", "Could not generate the oplog outline.");
    } finally {
        setState("idle");
    }
}
