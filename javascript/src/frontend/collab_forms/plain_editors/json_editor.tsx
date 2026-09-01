import * as Y from "yjs";
import { usePlainField } from "./field";
import { useState } from "react";

export default function JsonEditor(props: {
    connected: boolean;
    map: Y.Map<any>;
    mapKey: string;
}) {
    const [docValue, setDocValue] = usePlainField<string>(
        props.map,
        props.mapKey,
        "null"
    );
    // null means not open
    const [formValue, setFormValue] = useState<string | null>(null);

    if (formValue === null) {
        return (
            <>
                <textarea
                    readOnly
                    className="form-control no-auto-rich-text"
                    value={docValue}
                />
                <div className="json-editor-actions">
                    <button
                        type="button"
                        className="btn btn-outline-primary btn-sm"
                        onClick={() => setFormValue(docValue)}
                    >
                        Edit JSON
                    </button>
                </div>
            </>
        );
    }

    let error = null;
    try {
        JSON.parse(formValue);
    } catch (err) {
        error = (err as any).toString();
    }

    return (
        <>
            {error !== null && (
                <div className="alert alert-danger py-2" role="alert">
                    {error}
                </div>
            )}
            <textarea
                className="form-control no-auto-rich-text"
                value={formValue}
                onInput={(e) => {
                    setFormValue((e.target as HTMLTextAreaElement).value);
                }}
            />
            <div className="json-editor-actions">
                <button
                    type="button"
                    disabled={!props.connected || error !== null}
                    className="btn btn-primary btn-sm"
                    onClick={() => {
                        if (error !== null) return;
                        setDocValue(formValue);
                        setFormValue(null);
                    }}
                >
                    Save JSON
                </button>
                <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setFormValue(null)}
                >
                    Cancel
                </button>
            </div>
        </>
    );
}
