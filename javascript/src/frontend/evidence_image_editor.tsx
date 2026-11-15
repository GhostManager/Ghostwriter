import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import ReactModal from "react-modal";
import ImageAnnotator from "./image_annotator";
import { installEvidenceForm } from "./evidence_form";
import "./collab_forms/editor.scss";

const isImage = (name: string) => /\.(png|jpe?g)$/i.test(name);

type EditSession = {
    source: Blob | string;
    filename: string;
    files: FileList;
    disabled: boolean;
    submitControls: {
        control: HTMLButtonElement | HTMLInputElement;
        disabled: boolean;
    }[];
};

/** Stage lossless edits while preserving the file through form validation errors. */
export function EvidenceImageEditor(props: {
    input: HTMLInputElement;
    source: string;
    filename: string;
    refreshUrl?: string;
}) {
    const [file, setFile] = useState<File | null>(
        props.input.files?.[0] ?? null
    );
    const [session, setSession] = useState<EditSession | null>(null);
    const sessionRef = useRef<EditSession | null>(null);
    const [edited, setEdited] = useState(false);
    const [opening, setOpening] = useState(false);
    const [openError, setOpenError] = useState<string | null>(null);
    const openRequest = useRef<AbortController | null>(null);

    const setEditedFlag = (value: boolean) => {
        const flag = props.input.form?.elements.namedItem(
            "document_was_edited"
        );
        if (flag instanceof HTMLInputElement)
            flag.value = value ? "true" : "false";
    };

    const finishSession = (restoreFiles: boolean) => {
        const active = sessionRef.current;
        if (!active) return;
        if (restoreFiles) props.input.files = active.files;
        props.input.disabled = active.disabled;
        for (const { control, disabled } of active.submitControls)
            control.disabled = disabled;
        delete props.input.dataset.gwImageEditorOpen;
        sessionRef.current = null;
        setSession(null);
    };

    useEffect(() => {
        const change = (event: Event) => {
            if (sessionRef.current) {
                props.input.files = sessionRef.current.files;
                event.stopImmediatePropagation();
                return;
            }
            setFile(props.input.files?.[0] ?? null);
            setEdited(false);
            // An empty input after server-side validation must not erase the
            // reminder that the edited file still needs to be provided.
            if (props.input.files?.length) setEditedFlag(false);
        };
        const paste = (event: ClipboardEvent) => {
            if (!sessionRef.current || !event.clipboardData?.files.length)
                return;
            event.preventDefault();
            event.stopImmediatePropagation();
        };
        const submit = (event: Event) => {
            if (!sessionRef.current) return;
            event.preventDefault();
            event.stopImmediatePropagation();
        };
        const form = props.input.form;
        props.input.addEventListener("change", change, true);
        window.addEventListener("paste", paste, true);
        form?.addEventListener("submit", submit, true);
        return () => {
            openRequest.current?.abort();
            props.input.removeEventListener("change", change, true);
            window.removeEventListener("paste", paste, true);
            form?.removeEventListener("submit", submit, true);
            const active = sessionRef.current;
            if (active) {
                props.input.files = active.files;
                props.input.disabled = active.disabled;
                for (const { control, disabled } of active.submitControls)
                    control.disabled = disabled;
                delete props.input.dataset.gwImageEditorOpen;
            }
        };
    }, [props.input]);

    const beginSession = async () => {
        if (props.input.disabled || sessionRef.current) return;
        const snapshot = new DataTransfer();
        for (const selected of props.input.files ?? [])
            snapshot.items.add(selected);
        const active: EditSession = {
            source: file ?? props.source,
            filename: file?.name ?? props.filename,
            files: snapshot.files,
            disabled: props.input.disabled,
            submitControls: [
                ...(props.input.form?.querySelectorAll<
                    HTMLButtonElement | HTMLInputElement
                >('button[type="submit"], input[type="submit"]') ?? []),
            ].map((control) => ({ control, disabled: control.disabled })),
        };
        sessionRef.current = active;
        props.input.disabled = true;
        for (const { control } of active.submitControls)
            control.disabled = true;
        props.input.dataset.gwImageEditorOpen = "true";
        setOpenError(null);
        setOpening(true);
        const request = new AbortController();
        openRequest.current = request;
        try {
            // A staged file is the operator's unsaved work. Otherwise always
            // fetch the current server revision before opening the editor.
            if (!file && props.refreshUrl) {
                const response = await fetch(props.refreshUrl, {
                    headers: { Accept: "application/json" },
                    cache: "no-store",
                    signal: request.signal,
                });
                if (!response.ok) throw new Error("Could not load evidence");
                const latest = await response.json();
                if (
                    typeof latest.document !== "string" ||
                    typeof latest.download_url !== "string" ||
                    !isImage(latest.document)
                )
                    throw new Error("Image evidence is no longer available");
                const download = new URL(latest.download_url, location.href);
                if (download.origin !== location.origin)
                    throw new Error("Unexpected image location");
                download.searchParams.set("expected_document", latest.document);
                const image = await fetch(download, {
                    cache: "no-store",
                    signal: request.signal,
                });
                if (!image.ok)
                    throw new Error("Image changed or could not be loaded");
                const source = await image.blob();
                if (!/^image\/(png|jpeg)$/.test(source.type))
                    throw new Error("Image could not be loaded");
                active.source = source;
                active.filename = latest.document;
                const revision =
                    props.input.form?.elements.namedItem("expected_document");
                if (revision instanceof HTMLInputElement)
                    revision.value = latest.document;
            }
            if (!request.signal.aborted) setSession(active);
        } catch {
            if (!request.signal.aborted) {
                finishSession(true);
                setOpenError(
                    "The latest image could not be loaded. Please try opening it again."
                );
            }
        } finally {
            if (!request.signal.aborted) setOpening(false);
        }
    };

    if (!isImage(file?.name ?? props.filename)) return null;
    return (
        <div className="gw-evidence-annotate-row">
            <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                disabled={opening || props.input.disabled}
                onClick={beginSession}
            >
                <i className="fas fa-highlighter" aria-hidden="true" />
                {opening ? "Loading latest image…" : "Edit evidence image"}
            </button>
            <span className="form-text" role="status">
                {edited
                    ? "Image edits are ready. Use Save Changes below to save them."
                    : "Edit the image, then use Save Changes to save the evidence."}
            </span>
            {openError && (
                <span className="text-danger" role="alert">
                    {openError}
                </span>
            )}
            {session && (
                <ImageAnnotator
                    source={session.source}
                    saveLabel="Use edited image"
                    notice="These edits will replace the image everywhere this evidence is used in the report when you select Save Changes. The original is not kept as an undo version."
                    onCancel={() => finishSession(true)}
                    onSave={async (blob) => {
                        const stem = session.filename
                            .split(/[\\/]/)
                            .pop()!
                            .replace(/\.[^.]+$/, "");
                        const replacement = new File([blob], stem + ".png", {
                            type: "image/png",
                        });
                        const transfer = new DataTransfer();
                        transfer.items.add(replacement);
                        finishSession(false);
                        props.input.files = transfer.files;
                        props.input.dispatchEvent(
                            new Event("change", { bubbles: true })
                        );
                        setEditedFlag(true);
                        setEdited(true);
                    }}
                />
            )}
        </div>
    );
}

const host = document.getElementById("evidence-image-editor");
const input = document.querySelector<HTMLInputElement>("#id_document");
if (host && input) {
    if (input.form) installEvidenceForm(input.form);
    ReactModal.setAppElement(".resource-edit-page");
    createRoot(host).render(
        <EvidenceImageEditor
            input={input}
            source={host.dataset.source ?? ""}
            filename={host.dataset.filename ?? ""}
            refreshUrl={input.form?.action || location.href}
        />
    );
}
