import ReactModal from "react-modal";
import { ConnectionStatus, usePageConnection } from "../connection";
import { createRoot, Root } from "react-dom/client";
import RichTextEditor from "../rich_text_editor";

function ProjectCollabNoteForm() {
    const { provider, status, connected } = usePageConnection({
        model: "project",
    });

    return (
        <>
            <ConnectionStatus status={status} />
            <div className="form-group col-md-12">
                <div className="form-group col-md-12">
                    <RichTextEditor
                        connected={connected}
                        provider={provider}
                        fragment={provider.document.getXmlFragment(
                            "collabNote"
                        )}
                    />
                </div>
            </div>
        </>
    );
}

document.addEventListener("DOMContentLoaded", () => {
    ReactModal.setAppElement(
        document.querySelector("div.wrapper") as HTMLElement
    );

    const $ = (window as any).$;
    let root: Root | null = null;

    $("#id_collab_notes").on("shown.bs.tab", () => {
        if (root !== null) return;
        root = createRoot(document.getElementById("collab_notes_container")!);
        root.render(<ProjectCollabNoteForm />);
    });

    $("#id_collab_notes").on("hidden.bs.tab", () => {
        if (root !== null) root.unmount();
        root = null;
    });
});
