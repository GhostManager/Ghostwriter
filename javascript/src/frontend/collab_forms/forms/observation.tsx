import { createRoot } from "react-dom/client";

import { ConnectionStatus, usePageConnection } from "../connection";
import { PlainTextInput } from "../plain_editors";
import { TagEditor } from "../tag_editor";
import RichTextEditor from "../rich_text_editor";
import ExtraFieldsSection from "../extra_fields";
import ReactModal from "react-modal";

function ObservationForm() {
    const { provider, status, connected } = usePageConnection({
        model: "observation",
    });

    return (
        <div className="form-row">
            <div className="form-group col-md-6 mb-0">
                <div className="form-group">
                    <label htmlFor="id_title">Title</label>
                    <div>
                        <PlainTextInput
                            inputProps={{
                                id: "id_title",
                                className: "form-control",
                            }}
                            connected={connected}
                            provider={provider}
                            mapKey="title"
                        />
                    </div>
                </div>
            </div>
            <div className="form-group col-md-6 mb-0">
                <div className="form-group">
                    <label htmlFor="id_tags">Tags</label>
                    <div>
                        <TagEditor
                            id="id_tags"
                            className="form-control"
                            connected={connected}
                            provider={provider}
                            docKey="tags"
                        />
                    </div>
                </div>
            </div>

            <div className="form-group col-md-12">
                <label>Description</label>
                <div>
                    <RichTextEditor
                        connected={connected}
                        provider={provider}
                        fragment={provider.document.getXmlFragment(
                            "description"
                        )}
                    />
                </div>
            </div>

            <ExtraFieldsSection connected={connected} provider={provider} />

            <ConnectionStatus status={status} />
        </div>
    );
}

document.addEventListener("DOMContentLoaded", () => {
    ReactModal.setAppElement(
        document.querySelector("div.wrapper") as HTMLElement
    );
    const root = createRoot(document.getElementById("collab-form-container")!);
    root.render(<ObservationForm />);
});
