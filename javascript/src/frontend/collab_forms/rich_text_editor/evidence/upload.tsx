import { useContext, useEffect, useId, useRef, useState } from "react";
import { EvidencesContext } from "../../../../tiptap_gw/evidence";
import { getCsrfToken } from "../../../../services/csrf";
import ImageAnnotator from "../../../image_annotator";

type DjangoFormErrors = Record<string, string[]>;

export default function EvidenceUploadForm(props: {
    onSubmit: (id: number | null) => void;
    switchMode: () => void;
    initialFile?: File;
    onBusyChange?: (busy: boolean) => void;
}) {
    const evidences = useContext(EvidencesContext)!;
    const [state, setState] = useState<null | DjangoFormErrors | "loading">(
        null
    );
    // Pre-populate the friendly name based on the initial file name without the extension, if provided
    const [friendlyName, setFriendlyName] = useState<string>(
        props.initialFile ? props.initialFile.name.replace(/\.[^.]+$/, "") : ""
    );
    const formRef = useRef<HTMLFormElement | null>(null);
    const submitting = useRef(false);
    const friendlyNameId = useId();
    const captionId = useId();

    const disabled = state === "loading";
    const errors = state !== "loading" ? state : null;

    useEffect(() => () => props.onBusyChange?.(false), [props.onBusyChange]);

    return (
        <form
            ref={formRef}
            className="gw-evidence-upload-form"
            onSubmit={(ev) => {
                ev.preventDefault();
                if (submitting.current) return;
                submitting.current = true;
                props.onBusyChange?.(true);
                setState("loading");
                const data = new FormData(formRef.current!);

                (async () => {
                    const csrf = getCsrfToken();
                    if (!csrf) {
                        console.error(
                            "CSRF token is missing; aborting evidence upload."
                        );
                        setState({
                            form: [
                                "CSRF token not found. Please refresh the page.",
                            ],
                        });
                        submitting.current = false;
                        props.onBusyChange?.(false);
                        return;
                    }
                    const headers = new Headers();
                    headers.append("Accept", "application/json");
                    headers.append("X-CSRFToken", csrf);
                    const res = await fetch(evidences.uploadUrl, {
                        method: "POST",
                        headers,
                        body: data,
                    });
                    if (res.status === 200) {
                        const body = await res.json();
                        try {
                            await evidences.poll();
                        } catch {
                            // The evidence already exists. A failed refresh must
                            // not offer another upload of the same edited file.
                            console.warn(
                                "Evidence uploaded, but its preview could not be refreshed."
                            );
                        }
                        props.onBusyChange?.(false);
                        props.onSubmit(body.pk);
                    } else if (res.status === 400) {
                        const body = await res.json();
                        console.error(body);
                        setState(body);
                        submitting.current = false;
                        props.onBusyChange?.(false);
                    } else {
                        setState({ form: ["Could not create evidence"] });
                        submitting.current = false;
                        props.onBusyChange?.(false);
                    }
                })().catch((err) => {
                    console.error(err);
                    setState({ form: ["Could not create evidence"] });
                    submitting.current = false;
                    props.onBusyChange?.(false);
                });
            }}
        >
            <div className="modal-body gw-evidence-dialog-body">
                {state !== "loading" && state?.form && (
                    <div
                        className="alert alert-danger gw-evidence-upload-alert"
                        role="alert"
                    >
                        <ul>
                            {state.form.map((err, i) => (
                                <li key={i}>{err}</li>
                            ))}
                        </ul>
                    </div>
                )}

                <div className="form-group gw-evidence-upload-field">
                    <label htmlFor={friendlyNameId}>Friendly name</label>
                    <input
                        id={friendlyNameId}
                        name="friendly_name"
                        className={
                            "textinput textInput form-control " +
                            (errors?.friendly_name ? "is-invalid" : "")
                        }
                        required
                        type="text"
                        maxLength={255}
                        autoComplete="off"
                        placeholder="e.g., Kerberos ticket request"
                        disabled={disabled}
                        value={friendlyName}
                        onChange={(e) => setFriendlyName(e.target.value)}
                    />
                    <ErrorFeedback errors={errors?.friendly_name} />
                    <small className="form-text text-muted">
                        Use a short, recognizable name for references in the
                        editor.
                    </small>
                </div>

                <div className="form-group gw-evidence-upload-field">
                    <label htmlFor={captionId}>Caption</label>
                    <input
                        id={captionId}
                        name="caption"
                        className={
                            "textinput textInput form-control " +
                            (errors?.caption ? "is-invalid" : "")
                        }
                        required
                        type="text"
                        maxLength={255}
                        autoComplete="off"
                        placeholder="Describe what the evidence demonstrates"
                        disabled={disabled}
                    />
                    <ErrorFeedback errors={errors?.caption} />
                    <small className="form-text text-muted">
                        This one-line caption appears in the generated report.
                    </small>
                </div>

                <input type="hidden" name="tags" value="" />
                <input type="hidden" name="description" value="" />

                <FileInput
                    errors={errors}
                    disabled={disabled}
                    initialFile={props.initialFile}
                />
            </div>

            <div className="modal-footer gw-evidence-dialog-footer">
                <button
                    type="button"
                    className="btn btn-outline-secondary gw-evidence-mode-action"
                    disabled={disabled}
                    onClick={(e) => {
                        e.preventDefault();
                        props.switchMode();
                    }}
                >
                    <i className="fas fa-list" aria-hidden="true" />
                    Choose existing
                </button>
                <div className="gw-evidence-dialog-primary-actions">
                    <button
                        type="button"
                        className="btn btn-outline-secondary"
                        disabled={disabled}
                        onClick={(ev) => {
                            ev.preventDefault();
                            props.onSubmit(null);
                        }}
                    >
                        Cancel
                    </button>
                    <button
                        className="btn gw-evidence-primary-action"
                        type="submit"
                        disabled={disabled}
                    >
                        {disabled ? (
                            <>
                                <i
                                    className="fas fa-spinner fa-spin"
                                    aria-hidden="true"
                                />
                                Uploading…
                            </>
                        ) : (
                            <>
                                <i
                                    className="fas fa-upload"
                                    aria-hidden="true"
                                />
                                Upload and insert
                            </>
                        )}
                    </button>
                </div>
            </div>
        </form>
    );
}

const IMAGE_TYPES = /^image\/(png|jpeg)$/;

function FileInput(props: {
    errors: DjangoFormErrors | null;
    disabled: boolean;
    initialFile?: File;
}) {
    const id = useId();
    const fileRef = useRef<HTMLInputElement | null>(null);
    const [file, setFile] = useState<File | null>(props.initialFile ?? null);
    const [annotatorOpen, setAnnotatorOpen] = useState(false);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);

    useEffect(() => {
        if (!file || !IMAGE_TYPES.test(file.type)) {
            setPreviewUrl(null);
            return;
        }
        const url = URL.createObjectURL(file);
        setPreviewUrl(url);
        return () => URL.revokeObjectURL(url);
    }, [file]);

    // Keep the form's file input in sync with the selected (or edited) file
    const selectFile = (files: FileList | File | null) => {
        if (files instanceof File) {
            const dt = new DataTransfer();
            dt.items.add(files);
            files = dt.files;
        }
        if (files && fileRef.current) fileRef.current.files = files;
        setFile(files?.[0] ?? null);
    };

    // Pre-populate the file input when an initial file is provided (paste-to-upload)
    useEffect(() => {
        if (props.initialFile) selectFile(props.initialFile);
    }, [props.initialFile]);

    useEffect(() => {
        if (annotatorOpen || props.disabled) return;
        const cb = (ev: ClipboardEvent) => {
            if (ev.clipboardData?.files.length != 1) return;
            ev.preventDefault();
            selectFile(ev.clipboardData.files[0]);
        };
        document.addEventListener("paste", cb);
        return () => document.removeEventListener("paste", cb);
    }, [annotatorOpen, props.disabled]);

    const isImage = !!file && IMAGE_TYPES.test(file.type);

    return (
        <>
            <div
                className={
                    "gw-evidence-dropzone" +
                    (props.errors?.document ? " is-invalid" : "")
                }
                onDrop={(ev) => {
                    ev.preventDefault();
                    if (props.disabled || ev.dataTransfer.files.length !== 1)
                        return;
                    selectFile(ev.dataTransfer.files);
                }}
                onDragOver={(ev) => {
                    ev.preventDefault();
                }}
            >
                <input
                    name="document"
                    className="gw-evidence-file-input"
                    type="file"
                    accept=".txt,.log,.md,.png,.jpg,.jpeg"
                    required
                    disabled={props.disabled}
                    id={id}
                    ref={fileRef}
                    onChange={(ev) => setFile(ev.target.files?.[0] ?? null)}
                />
                <label className="gw-evidence-dropzone-label" htmlFor={id}>
                    <span
                        className="gw-evidence-dropzone-icon"
                        aria-hidden="true"
                    >
                        <i className="fas fa-cloud-upload-alt" />
                    </span>
                    <span className="gw-evidence-dropzone-copy">
                        <span
                            className="gw-evidence-dropzone-title"
                            aria-live="polite"
                        >
                            {file?.name ?? "Choose, drop, or paste a file"}
                        </span>
                        <span className="gw-evidence-dropzone-help">
                            TXT, LOG, MD, PNG, JPG, or JPEG
                        </span>
                    </span>
                </label>
            </div>
            <ErrorFeedback errors={props.errors?.document} />
            {previewUrl && (
                <img
                    className="gw-evidence-upload-preview"
                    src={previewUrl}
                    alt="Selected evidence preview"
                />
            )}
            {isImage && (
                <div className="gw-evidence-annotate-row">
                    <button
                        type="button"
                        className="btn btn-sm btn-outline-secondary"
                        disabled={props.disabled}
                        onClick={() => setAnnotatorOpen(true)}
                    >
                        <i className="fas fa-highlighter" aria-hidden="true" />
                        Edit image before uploading
                    </button>
                    <small className="form-text text-muted">
                        Censor, highlight, or crop it first. Edits are applied
                        before upload, so the original image never leaves your
                        browser.
                    </small>
                </div>
            )}
            {annotatorOpen && file && (
                <ImageAnnotator
                    source={file}
                    saveLabel="Use edited image"
                    onCancel={() => setAnnotatorOpen(false)}
                    onSave={async (blob) => {
                        const stem = file.name.replace(/\.[^.]+$/, "");
                        selectFile(
                            new File([blob], stem + ".png", {
                                type: "image/png",
                            })
                        );
                        setAnnotatorOpen(false);
                    }}
                />
            )}
        </>
    );
}

function ErrorFeedback(props: {
    errors: DjangoFormErrors[string] | null | undefined;
}) {
    if (
        props.errors === null ||
        props.errors === undefined ||
        props.errors.length === 0
    )
        return null;
    return (
        <div className="invalid-feedback">
            <ul>
                {props.errors.map((e, i) => (
                    <li key={i}>{e}</li>
                ))}
            </ul>
        </div>
    );
}
