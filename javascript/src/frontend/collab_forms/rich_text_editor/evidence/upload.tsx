import { useContext, useEffect, useId, useRef, useState } from "react";
import { EvidencesContext } from "../../../../tiptap_gw/evidence";
import { getCsrfToken } from "../../../../services/csrf";

type DjangoFormErrors = Record<string, string[]>;

export default function EvidenceUploadForm(props: {
    onSubmit: (id: number | null) => void;
    switchMode: () => void;
    initialFile?: File;
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
    const friendlyNameId = useId();
    const captionId = useId();

    const disabled = state === "loading";
    const errors = state !== "loading" ? state : null;

    return (
        <form
            ref={formRef}
            className="gw-evidence-upload-form"
            onSubmit={(ev) => {
                ev.preventDefault();
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
                        await evidences?.poll();
                        props.onSubmit(body.pk);
                    } else if (res.status === 400) {
                        const body = await res.json();
                        console.error(body);
                        setState(body);
                    } else {
                        setState({ form: ["Could not create evidence"] });
                    }
                })().catch((err) => {
                    console.error(err);
                    setState({ form: ["Could not create evidence"] });
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

function FileInput(props: {
    errors: DjangoFormErrors | null;
    disabled: boolean;
    initialFile?: File;
}) {
    const id = useId();
    const fileRef = useRef<HTMLInputElement | null>(null);
    const [fileName, setFileName] = useState<string | null>(
        props.initialFile?.name ?? null
    );

    // Pre-populate the file input when an initial file is provided (paste-to-upload)
    useEffect(() => {
        if (!props.initialFile || !fileRef.current) return;
        const dt = new DataTransfer();
        dt.items.add(props.initialFile);
        fileRef.current.files = dt.files;
    }, [props.initialFile]);

    useEffect(() => {
        const cb = (ev: ClipboardEvent) => {
            if (ev.clipboardData?.files.length != 1) return;
            ev.preventDefault();
            fileRef.current!.files = ev.clipboardData.files;
            setFileName(ev.clipboardData.files[0].name);
        };
        document.addEventListener("paste", cb);
        return () => document.removeEventListener("paste", cb);
    }, [fileRef]);

    return (
        <>
            <div
                className={
                    "gw-evidence-dropzone" +
                    (props.errors?.document ? " is-invalid" : "")
                }
                onDrop={(ev) => {
                    ev.preventDefault();
                    if (ev.dataTransfer.files.length !== 1) return;
                    fileRef.current!.files = ev.dataTransfer.files;
                    setFileName(ev.dataTransfer.files[0].name);
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
                    onChange={(ev) => {
                        if (ev.target.files?.length)
                            setFileName(ev.target.files[0].name);
                        else setFileName(null);
                    }}
                />
                <label className="gw-evidence-dropzone-label" htmlFor={id}>
                    <span
                        className="gw-evidence-dropzone-icon"
                        aria-hidden="true"
                    >
                        <i className="fas fa-cloud-upload-alt" />
                    </span>
                    <span className="gw-evidence-dropzone-copy">
                        <span className="gw-evidence-dropzone-title">
                            {fileName ?? "Choose, drop, or paste a file"}
                        </span>
                        <span className="gw-evidence-dropzone-help">
                            TXT, LOG, MD, PNG, JPG, or JPEG
                        </span>
                    </span>
                </label>
            </div>
            <ErrorFeedback errors={props.errors?.document} />
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
