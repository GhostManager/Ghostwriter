import ReactModal from "react-modal";
import { ConnectionStatus, usePageConnection } from "../connection";
import { createRoot } from "react-dom/client";
import { ExtraFieldInput, useExtraFieldSpecs } from "../extra_fields";

function ReportExtraFieldForm(props: { field: string }) {
    const { provider, status, connected } = usePageConnection({
        model: "report",
    });

    const extraFields = useExtraFieldSpecs();
    const extraField = extraFields.find((v) => v.internal_name === props.field);
    if (!extraField) {
        console.log("Available fields", extraFields);
        throw new Error("Missing extra field:" + props.field);
    }

    return (
        <>
            <ConnectionStatus status={status} />
            <div className="form-group col-md-12">
                <ExtraFieldInput
                    connected={connected}
                    provider={provider}
                    spec={extraField}
                />
                {extraField.description && (
                    <small className="form-text text-muted">
                        {extraField.description}
                    </small>
                )}
            </div>
        </>
    );
}

document.addEventListener("DOMContentLoaded", () => {
    ReactModal.setAppElement(
        document.querySelector("div.wrapper") as HTMLElement
    );
    const el = document.getElementById("collab-form-container")!;
    const fieldName = el.getAttribute("data-extra-field-name")!;
    const root = createRoot(el);
    root.render(<ReportExtraFieldForm field={fieldName} />);
});
