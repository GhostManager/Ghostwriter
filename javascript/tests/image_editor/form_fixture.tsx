import { useEffect, useState } from "react";
import { EvidenceImageEditor } from "../../src/frontend/evidence_image_editor";
import { installEvidenceForm } from "../../src/frontend/evidence_form";

export function EvidenceFormFixture({ source }: { source: string }) {
    const [form, setForm] = useState<HTMLFormElement | null>(null);
    const [input, setInput] = useState<HTMLInputElement | null>(null);
    useEffect(() => (form ? installEvidenceForm(form) : undefined), [form]);
    return (
        <form ref={setForm} action="/test-evidence-save" method="post">
            <input
                type="hidden"
                name="csrfmiddlewaretoken"
                value="fixture-csrf-token"
            />
            <input
                type="hidden"
                name="expected_document"
                defaultValue="old.png"
            />
            <input
                type="hidden"
                name="document_was_edited"
                defaultValue="false"
            />
            <label>
                Friendly name
                <input name="friendly_name" defaultValue="Proof" required />
            </label>
            <label>
                Caption
                <input
                    name="caption"
                    defaultValue="Original caption"
                    required
                />
            </label>
            <label>
                Description
                <textarea
                    name="description"
                    defaultValue="Original description"
                />
            </label>
            <input ref={setInput} type="file" name="document" />
            <input aria-label="Originally disabled" name="disabled" disabled />
            {input && (
                <EvidenceImageEditor
                    input={input}
                    source={source}
                    filename={
                        new URLSearchParams(location.search).has("blank")
                            ? ""
                            : "old.png"
                    }
                    refreshUrl="/test-evidence-metadata"
                />
            )}
            <div className="resource-form-actions">
                <a href="/cancelled">Cancel</a>
                <button type="submit">Save Changes</button>
            </div>
        </form>
    );
}
