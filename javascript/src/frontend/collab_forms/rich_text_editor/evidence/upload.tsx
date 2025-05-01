import { useContext, useEffect, useId, useRef, useState } from "react";
import { EvidencesContext } from "../../../../tiptap_gw/evidence";

type DjangoFormErrors = Record<string, string[]>;

export default function EvidenceUploadForm(props: {
    onSubmit: (id: number | null) => void;
    switchMode: () => void;
}) {
    const evidences = useContext(EvidencesContext)!;
    const [state, setState] = useState<null | DjangoFormErrors | "loading">(
        null
    );
    const formRef = useRef<HTMLFormElement | null>(null);
    const friendlyNameId = useId();
    const captionId = useId();

    const disabled = state === "loading";
    const errors = state !== "loading" ? state : null;

    return (
        <form
            ref={formRef}
            onSubmit={(ev) => {
                ev.preventDefault();
                setState("loading");
                const data = new FormData(formRef.current!);

                (async () => {
                    const csrf = document.cookie
                        .split("; ")
                        .find((row) => row.startsWith("csrftoken="))
                        ?.split("=")[1];
                    const headers = new Headers();
                    headers.append("Accept", "application/json");
                    headers.append("X-CSRFToken", csrf!);
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
            <div className="modal-body">
                {state !== "loading" && state?.form && (
                    <div className="alert alert-danger" role="alert">
                        <ul>
                            {state.form.map((err, i) => (
                                <li key={i}>{err}</li>
                            ))}
                        </ul>
                    </div>
                )}

                <div className="form-group">
                    <label htmlFor={friendlyNameId}>Friendly Name</label>
                    <div>
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
                            placeholder="Friendly Name"
                            disabled={disabled}
                        />
                        <ErrorFeedback errors={errors?.friendly_name} />
                        <small>
                            Provide a simple name to be used to reference this
                            evidence
                        </small>
                    </div>
                </div>

                <div className="form-group">
                    <label htmlFor={captionId}>Caption</label>
                    <div>
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
                            placeholder="Caption"
                            disabled={disabled}
                        />
                        <ErrorFeedback errors={errors?.caption} />
                        <small>
                            Provide a one line caption to be used in the report
                            - keep it brief
                        </small>
                    </div>
                </div>

                <input type="hidden" name="tags" value="" />
                <input type="hidden" name="description" value="" />

                <FileInput errors={errors} disabled={disabled} />
            </div>

            <div className="modal-footer">
                <button
                    className="btn btn-secondary"
                    onClick={(e) => {
                        e.preventDefault();
                        props.switchMode();
                    }}
                >
                    Select Existing
                </button>
                <input
                    className="btn btn-primary"
                    type="submit"
                    value="Submit"
                />
                <button
                    className="btn btn-outline-secondary"
                    onClick={(ev) => {
                        ev.preventDefault();
                        props.onSubmit(null);
                    }}
                >
                    Cancel
                </button>
            </div>
        </form>
    );
}

function FileInput(props: {
    errors: DjangoFormErrors | null;
    disabled: boolean;
}) {
    const id = useId();
    const fileRef = useRef<HTMLInputElement | null>(null);
    const [fileName, setFileName] = useState<string | null>(null);

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
            <p>
                Attach or paste text evidence (*.txt, *.log, or *.md) or image
                evidence (*.png, *.jpg, or *.jpeg).
            </p>
            <div
                className="custom-file"
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
                <div className="form-group">
                    <div className="mb-2">
                        <div
                            className={
                                "form-control custom-file" +
                                (props.errors?.document ? "is-invalid" : "")
                            }
                            style={{ border: 0 }}
                        >
                            <input
                                name="document"
                                className="custom-file-input"
                                type="file"
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
                            <label
                                className="custom-file-label text-truncate"
                                htmlFor={id}
                            >
                                {fileName ?? "No File Selected"}
                            </label>
                        </div>
                    </div>
                    <ErrorFeedback errors={props.errors?.document} />
                </div>
            </div>
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
