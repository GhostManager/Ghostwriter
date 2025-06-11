import ReactModal from "react-modal";
import { Editor } from "@tiptap/core";
import { createRoot } from "react-dom/client";

import { usePageConnection } from "../connection";
import { FindingFormFields } from "../forms_common/finding";
import PageGraphqlProvider from "../../graphql/client";
import { ProvidePageEvidence } from "../../graphql/evidence";
import EvidenceButton from "../rich_text_editor/evidence";
import RichTextEditor from "../rich_text_editor";

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
            extraTop={
                <>
                    <h4 className="icon list-icon">Affected Entities</h4>
                    <div className="form-group col-md-12">
                        <label htmlFor="collab-form-affected-entities">
                            Affected Entities
                        </label>
                        <div>
                            <RichTextEditor
                                provider={provider}
                                connected={connected}
                                fragment={provider.document.getXmlFragment(
                                    "affectedEntities"
                                )}
                                toolbarExtra={renderToolbarExtra}
                            />
                            <small className="form-text text-muted">
                                Provide a list of the affected entities (e.g.
                                domains, hostnames, IP addresses)
                            </small>
                        </div>
                    </div>
                </>
            }
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
