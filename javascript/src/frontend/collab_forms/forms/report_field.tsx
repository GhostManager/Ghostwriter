import ReactModal from "react-modal";
import { ConnectionStatus, usePageConnection } from "../connection";
import { createRoot } from "react-dom/client";
import { ExtraFieldInput, useExtraFieldSpecs } from "../extra_fields";
import { Editor } from "@tiptap/core";
import EvidenceButton from "../rich_text_editor/evidence";
import OplogOutlineButton from "../rich_text_editor/oplog_outline";
import PageGraphqlProvider from "../../graphql/client";
import { ProvidePageEvidence } from "../../graphql/evidence";
import ErrorBoundary from "../error_boundary";

const renderToolbarExtra = (editor: Editor) => (
    <>
        <EvidenceButton editor={editor} />
        <OplogOutlineButton editor={editor} />
    </>
);

function ReportExtraFieldForm(props: { field: string }) {
    const { provider, status, connected, setEditing } = usePageConnection({
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
            <div className="form-group col-md-12 report-field-form-group">
                <ExtraFieldInput
                    connected={connected}
                    provider={provider}
                    spec={extraField}
                    toolbarExtra={renderToolbarExtra}
                    setEditing={setEditing}
                />
            </div>
            <footer className="report-field-footer">
                {extraField.description && (
                    <small className="form-text text-muted">
                        {extraField.description}
                    </small>
                )}
                <ConnectionStatus status={status} />
            </footer>
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
    root.render(
        <ErrorBoundary>
            <PageGraphqlProvider>
                <ProvidePageEvidence>
                    <ReportExtraFieldForm field={fieldName} />
                </ProvidePageEvidence>
            </PageGraphqlProvider>
        </ErrorBoundary>
    );
});
