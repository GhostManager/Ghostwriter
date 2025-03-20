import ReactModal from "react-modal";
import { Editor } from "@tiptap/core";
import { createRoot } from "react-dom/client";

import { usePageConnection } from "../connection";
import { FindingFormFields } from "../forms_common/finding";
import PageGraphqlProvider from "../../graphql/client";
import { ProvidePageEvidence } from "../../graphql/evidence";
import EvidenceButton from "../rich_text_editor/evidence";

const renderToolbarExtra = (editor: Editor) => (
    <EvidenceButton editor={editor} />
);

function ReportFindingLinkForm() {
    const { provider, status, connected } = usePageConnection({
        model: "report_finding_link",
    });

    return (
        <FindingFormFields
            provider={provider}
            status={status}
            connected={connected}
            toolbarExtra={renderToolbarExtra}
        />
    );
}

document.addEventListener("DOMContentLoaded", () => {
    ReactModal.setAppElement(
        document.querySelector("div.wrapper") as HTMLElement
    );
    const root = createRoot(document.getElementById("collab-form-container")!);
    root.render(
        <PageGraphqlProvider>
            <ProvidePageEvidence>
                <ReportFindingLinkForm />
            </ProvidePageEvidence>
        </PageGraphqlProvider>
    );
});
