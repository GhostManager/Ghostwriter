import { createRoot } from "react-dom/client";
import ReactModal from "react-modal";

import PageGraphqlProvider from "../../graphql/client";
import { usePageConnection } from "../connection";
import { FindingFormFields } from "../forms_common/finding";
import RichTextEditor from "../rich_text_editor";

function FindingForm() {
    const { provider, status, connected } = usePageConnection({
        model: "finding",
    });

    return (
        <FindingFormFields
            provider={provider}
            status={status}
            connected={connected}
            extraBottom={
                <>
                    <div className="form-group col-md-12">
                        <label>Finding Guidance</label>
                        <div>
                            <RichTextEditor
                                connected={connected}
                                provider={provider}
                                fragment={provider.document.getXmlFragment(
                                    "findingGuidance"
                                )}
                            />
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
            <FindingForm />
        </PageGraphqlProvider>
    );
});
