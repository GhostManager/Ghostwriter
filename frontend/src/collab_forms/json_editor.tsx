import * as Y from "yjs";
import { usePlainField } from "./plain_editors";
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
                    className="form-control no-auto-tinymce"
                    value={docValue}
                />
                <button
                    className="btn"
                    onClick={(e) => {
                        e.preventDefault();
                        setFormValue(docValue);
                    }}
                >
                    Edit JSON
                </button>
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
            {error !== null && <div>{error}</div>}
            <textarea
                className="form-control no-auto-tinymce"
                value={formValue}
                onInput={(e) => {
                    setFormValue((e.target as HTMLTextAreaElement).value);
                }}
            />
            <button
                disabled={!props.connected}
                className="btn"
                onClick={(e) => {
                    e.preventDefault();
                    if (error !== null) return;
                    setDocValue(formValue);
                    setFormValue(null);
                }}
            >
                Save JSON
            </button>
        </>
    );
}
